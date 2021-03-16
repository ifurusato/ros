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
# An asyncio-based publish/subscribe-style message bus.
#
# See: https://roguelynn.com/words/asyncio-true-concurrency/
#

import asyncio, signal, traceback
import sys
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
        self._loop = asyncio.get_event_loop()
        self._queue = asyncio.Queue()
        self._publishers  = []
        self._subscribers = []
        # may want to catch other signals too
        signals = (signal.SIGHUP, signal.SIGTERM, signal.SIGINT)
        for s in signals:
            self._loop.add_signal_handler(
                s, lambda s=s: asyncio.create_task(self.shutdown(s)))
        self._loop.set_exception_handler(self.handle_exception)
        _garbage_collector = GarbageCollector('gc', Fore.RED, self, Level.INFO)
        self._subscribers.append(_garbage_collector)
        self._enabled    = True # by default
        self._closed     = False
        self._log.info('ready.')

    # ..........................................................................
    @property
    def queue(self):
        return self._queue

    # ..........................................................................
    @property
    def queue_size(self):
        return self._queue.qsize()

    # ..........................................................................
    def register_publisher(self, publisher):
        self._publishers.append(publisher)
        self._loop.create_task(publisher.publish())
        self._log.info('registered publisher \'{}\'; {:d} publishers in list.'.format(subscriber.name, len(self._subscribers)))

    # ..........................................................................
    def print_publishers(self):
        self._log.info('{:d} publishers in list:'.format(len(self._publishers)))
        for publisher in self._publishers:
            self._log.info('    publisher: {}'.format(publisher.name))

    # ..........................................................................
    def register_subscriber(self, subscriber):
        self._subscribers.insert(0, subscriber)
        self._log.info('registered subscriber \'{}\'; {:d} subscribers in list.'.format(subscriber.name, len(self._subscribers)))

    # ..........................................................................
    def print_subscribers(self):
        self._log.info('{:d} subscribers in list:'.format(len(self._subscribers)))
        for subscriber in self._subscribers:
            self._log.info('    subscriber: {}'.format(subscriber.name))

    # ..........................................................................
    async def consume(self):
        '''
        Start the subscribers' consume cycle.
        '''
        while self._enabled:
            for subscriber in self._subscribers:
                self._log.debug('publishing to subscriber {}...'.format(subscriber.name))
                await subscriber.consume()

    # ..........................................................................
    def consume_message(self):
        '''
        Asynchronously waits until it pops a message from the queue.

        NOTE: calls to this function should be await'd.
        '''
        return self._queue.get()

    # ..........................................................................
    def publish_message(self, message):
        '''
        Asynchronously publishes the Message to the MessageBus, and therefore to any Subscribers.

        NOTE: calls to this function should be await'd.
        '''
        if ( message.event is not Event.CLOCK_TICK and message.event is not Event.CLOCK_TOCK ):
            self._log.info('publishing message: {} (event: {});'.format(message.name, message.event))
        asyncio.create_task(self._queue.put(message))

    # ..........................................................................
    def republish_message(self, message):
        '''
        Asynchronously re-publishes the Message to the MessageBus, and therefore to any Subscribers.
        This isn't any different than publishing but we might start treating it differently.

        NOTE: calls to this function should be await'd.
        '''
        if ( message.event is not Event.CLOCK_TICK and message.event is not Event.CLOCK_TOCK ):
            self._log.info(Fore.BLACK + 'republishing message: {} (event: {});'.format(message.name, message.event))
            asyncio.create_task(self._queue.put(message))
        else:
            self._log.warning(Fore.BLACK + 'ignoring republication of message: {} (event: {});'.format(message.name, message.event))


    # exception handling .......................................................

    def handle_exception(self, loop, context):
        self._log.error('handle exception on loop: {}'.format(loop))
        # context["message"] will always be there; but context["exception"] may not
        message = context.get("exception", context["message"])
        self._log.error('caught exception: {}'.format(message))
#       self._log.error('caught exception: {} / {}'.format(message, traceback.print_stack()))
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

    @property
    def count(self):
        return len(self._subscribers)

    # ..........................................................................
    @property
    def enabled(self):
        return self._enabled

    # ..........................................................................
    def enable(self):
        if not self._closed:
            self._enabled = True
            if not self._loop.is_running():
                self._log.info(Fore.BLUE + 'creating task for subscribers...')
                self._loop.create_task(self.consume())
                self._log.info(Fore.BLUE + 'run forever...')
                self._loop.run_forever()
            self._log.info('enabled.')
        else:
            self._log.warning('cannot enable: already closed.')

    # ..........................................................................
    def disable(self):
        if self._enabled:
            self._enabled = False
            for publisher in self._publishers:
                '''
                NOTE: we are at this point incidentally tying publishing with
                the enabled state of the publisher. This may not be desired.
                '''
                publisher.disable()
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
