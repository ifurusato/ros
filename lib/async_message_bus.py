#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# Copyright 2020-2021 by Murray Altheim. All rights reserved. This file is part
# of the Robot Operating System project, released under the MIT License. Please
# see the LICENSE file included as part of this package.
#
# author:   Murray Altheim
# created:  2021-03-10
# modified: 2021-03-13
#
# An asyncio-based publish/subscribe-style message bus guaranteeing exactly-once
# delivery for each message. This is done by populating each message with the
# list of subscribers.
#
# Delivery guarantees:
#
#  * At-most-once delivery. This means that a message will never be delivered
#    more than once but messages might be lost.
#  * At-least-once delivery. This means that we'll never lose a message but a
#    message might end up being delivered to a consumer more than once.
#  * Exactly-once delivery. The holy grail of messaging. All messages will be
#    delivered exactly one time.
#

import asyncio, signal, traceback
import sys, logging
from colorama import init, Fore, Style
init()

from lib.logger import Logger, Level
from lib.event import Event
from lib.message import Message
from lib.subscriber import GarbageCollector

# ..............................................................................
class MessageBus(object):
    '''
    An asyncio-based asynchronous message bus.
    '''
    def __init__(self, level):
        self._log = Logger("bus", level)
        if level is Level.DEBUG:
            self._log.debug(Fore.YELLOW + 'logging message bus set to debug level.')
            logging.basicConfig(level=logging.DEBUG)
        self._loop        = asyncio.get_event_loop()
        self._queue       = asyncio.Queue()
        self._publishers  = []
        self._subscribers = []
        # may want to catch other signals too
        signals = (signal.SIGHUP, signal.SIGTERM, signal.SIGINT)
        for s in signals:
            self._loop.add_signal_handler(
                s, lambda s = s: asyncio.create_task(self.shutdown(s)))
        self._loop.set_exception_handler(self.handle_exception)
        self._garbage_collector = GarbageCollector('gc', Fore.RED, self, Level.INFO)
        self.register_subscriber(self._garbage_collector)

        self._max_age     = 5.0 # ms
        self._verbose     = True
        self._enabled     = True # by default
        self._closed      = False
        self._log.info('creating subscriber task...')
        self._loop.create_task(self.start_consuming())
        self._log.info('ready.')

    # ..........................................................................
    @property
    def queue(self):
        return self._queue

    @property
    def queue_size(self):
        return self._queue.qsize()

    # ..........................................................................
    @property
    def verbose(self):
        return self._verbose

    @verbose.setter
    def verbose(self, verbose):
        self._verbose = verbose

    # ..........................................................................
    def register_publisher(self, publisher):
        '''
        Register a message publisher with the message bus.
        '''
        self._publishers.append(publisher)
        self._loop.create_task(publisher.publish())
        self._log.info('registered publisher \'{}\'; {:d} publisher{} in list.'.format( \
                publisher.name, 
                len(self._publishers),
                's' if len(self._publishers) > 1 else ''))

    def print_publishers(self):
        '''
        Print the message publishers that have been registered with the message bus.
        '''
        if not self._publishers:
            self._log.info('no registered publishers.')
            return
        self._log.info('{:d} publisher{} in list:'.format( \
                len(self._publishers),
                's' if len(self._publishers) > 1 else ''))
        for publisher in self._publishers:
            self._log.info('  publisher: {}'.format(publisher.name))

    @property
    def publishers(self):
        return self._publishers

    @property
    def publisher_count(self):
        return len(self._publishers)

    # ..........................................................................
    def register_subscriber(self, subscriber):
        '''
        Register a message subscriber with the message bus.
        '''
        self._subscribers.insert(0, subscriber)
        self._loop.create_task(subscriber.consume())
        self._log.info('registered subscriber \'{}\'; {:d} subscriber{} in list.'.format( \
                subscriber.name, 
                len(self._subscribers),
                's' if len(self._subscribers) > 1 else ''))

    def print_subscribers(self):
        '''
        Print the message subscribers that have been registered with the message bus.
        '''
        if not self._subscribers:
            self._log.info('no registered subscribers.')
            return
        self._log.info('{:d} subscriber{} in list:'.format( \
                len(self._subscribers),
                's' if len(self._subscribers) > 1 else ''))
        for subscriber in self._subscribers:
            self._log.info('  subscriber: \'{}\' listening for: {}'.format(subscriber.name, subscriber.print_events()))

    @property
    def subscribers(self):
        return self._subscribers

    @property
    def subscriber_count(self):
        return len(self._subscribers)

    # ..........................................................................
    def is_expired(self, message):
        return message.age > self._max_age

    # ..........................................................................
    async def start_consuming(self):
        '''
        Start the subscribers' consume cycle. This remains active until the
        message bus is disabled.
        '''
        self._log.info('begin {:d} subscribers\' consume cycle...'.format(len(self._subscribers)))
        while self._enabled:
            for subscriber in self._subscribers:
                self._log.debug('publishing to subscriber {}...'.format(subscriber.name))
                await subscriber.consume()

    # ..........................................................................
    def print_bus_info(self):
        self._log.info('message bus info:' + Fore.YELLOW + ' {:d} messages in queue; {:d} publisher{}, {:d} subscriber{}.'.format( \
                self._queue.qsize(),
                len(self._publishers),
                's' if len(self._publishers) > 1 else '',
                len(self._subscribers),
                's' if len(self._subscribers) > 1 else ''))
        pass # TODO

    # ..........................................................................
    def consume_message(self):
        '''
        Asynchronously waits until it pops a message from the queue.

        NOTE: calls to this function should be await'd, and every call should correspond with a call to task_done().
        '''
        return self._queue.get()

    # ..........................................................................
    def task_done(self):
        '''
        Every call to consume_message() should correspond with a call to task_done().
        '''
        self._queue.task_done()

    # ..........................................................................
    def publish_message(self, message):
        '''
        Asynchronously publishes the Message to the MessageBus, and therefore to any Subscribers.

        NOTE: calls to this function should be await'd.
        '''
        if ( message.event is not Event.CLOCK_TICK and message.event is not Event.CLOCK_TOCK ):
            self._log.info(Style.BRIGHT + 'publishing message: {}'.format(message.name) + Style.NORMAL + ' (event: {}; age: {:d}ms);'.format(message.event, message.age))
        _result = asyncio.create_task(self._queue.put(message))
        self._log.debug('result from published message: {}'.format(type(_result)))

    # ..........................................................................
    async def republish_message(self, message):
        '''
        Asynchronously re-publishes the Message to the MessageBus, and therefore to any Subscribers.
        This isn't any different than publishing but we might start treating it differently, e.g.,
        altering the message state.

        NOTE: calls to this function should be await'd. Fully-acknowledged messages are ignored.
        '''
        if message.fully_acknowledged:
            self._log.warning(Fore.BLACK + 'ignoring republication of fully-acknowledged message: {} (event: {});'.format(message.name, message.event))
        elif ( message.event is not Event.CLOCK_TICK and message.event is not Event.CLOCK_TOCK ):
            self._log.info(Fore.YELLOW + Style.BRIGHT + 'REPUBLISHING message: {} (event: {}; age: {:d}ms);'.format(message.name, message.event, message.age))
            asyncio.create_task(self._queue.put(message))
        else:
            self._log.warning(Fore.BLACK + 'ignoring republication of message: {} (event: {});'.format(message.name, message.event))

    # ..........................................................................
    def garbage_collect(self, message):
        '''
        Explicitly garbage collect the message, returning True if gc'd.
        '''
        return self._garbage_collector.collect(message)

    # exception handling .......................................................
    def handle_exception(self, loop, context):
        self._log.error('handle exception on loop: {}'.format(loop))
        # context["message"] will always be there; but context["exception"] may not
        _exception = context.get('exception', context['message'])
        if _exception != None:
            self._log.error('caught {}: {}'.format(type(_exception), _exception))
        else:
            self._log.error('caught exception: {}'.format(context.get('message')))
        if loop.is_running() and not loop.is_closed():
            asyncio.create_task(self.shutdown(loop))
        else:
            self._log.info("loop already shut down.")

    # shutdown .....................................................................
    async def shutdown(self, signal=None):
        '''
        Cleanup tasks tied to the service's shutdown.
        '''
        if signal:
            self._log.info('received exit signal {}...'.format(signal))
#       self._log.info(Fore.RED + 'closing services...' + Style.RESET_ALL)
        self._log.info(Fore.RED + 'nacking outstanding tasks...' + Style.RESET_ALL)
        tasks = [t for t in asyncio.all_tasks() if t is not
                asyncio.current_task()]
        [task.cancel() for task in tasks]
        self._log.info(Fore.RED + 'cancelling {:d} outstanding tasks...'.format(len(tasks)) + Style.RESET_ALL)
        await asyncio.gather(*tasks, return_exceptions=True)
        self._log.info(Fore.RED + "stopping loop..." + Style.RESET_ALL)
        self._loop.stop()
        self._log.info(Fore.RED + "shutting down..." + Style.RESET_ALL)
        sys.exit(1) # really?

    # ..........................................................................
    @property
    def enabled(self):
        return self._enabled

    # ..........................................................................
    def enable(self):
        if not self._closed:
            self._enabled = True
            self._log.info('enabled.')
            if not self._loop.is_running():
                self._log.info('starting asyncio task loop...')
                self._loop.run_forever()
            self._log.info('exited forever loop.')
        else:
            self._log.warning('cannot enable: already closed.')

    # ..........................................................................
    def disable(self):
        '''
        NOTE: we are at this point incidentally tying publishing with
        the enabled state of the publisher, and subscribing with the
        enabled state of the subscriber. This may not be desired.
        '''
        if self._enabled:
            self._enabled = False
            for publisher in self._publishers:
                publisher.disable()
            for subscriber in self._subscribers:
                subscriber.disable()
            if self._loop.is_running():
                self._loop.stop()
            self._log.info('disabled.')
        else:
            self._log.warning('already disabled.')

    # ..........................................................................
    def close(self):
        '''
        Permanently close and disable the message bus.
        '''
        if not self._closed:
            self.disable()
            self._closed = True
            self._log.info('closed.')
        else:
            self._log.debug('already closed.')

#EOF
