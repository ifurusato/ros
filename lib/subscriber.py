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

import asyncio
import random
from typing import final
from datetime import datetime as dt
from colorama import init, Fore, Style
init()

from lib.logger import Logger, Level
from lib.event import Event

LOG_INDENT = ( ' ' * 60 ) + Fore.CYAN + ': ' + Fore.CYAN

# SaveFailed exception .........................................................
class SaveFailed(Exception):
    pass

# RestartFailed exception ......................................................
class RestartFailed(Exception):
    pass

# Subscriber ...................................................................
class Subscriber(object):
    '''
    A subscriber to messages from the message bus.

    :param name:         the subscriber name (for logging)
    :param color:        the color to use for printing
    :param message_bus:  the message bus
    :param events:       the list of events used as a filter, None to set as cleanup task
    :param level:        the logging level
    '''
    def __init__(self, name, color, message_bus, level=Level.INFO):
        self._log = Logger('sub-{}'.format(name), level)
        self._name        = name
        self._color       = color
        self._message_bus = message_bus
        self._events      = None # list of acceptable event types
        self._enabled     = True # by default
        self._log.info(self._color + 'ready.')

    # ..........................................................................
    @property
    def name(self):
        return self._name

    # ..........................................................................
    @property
    def is_gc(self):
        return False

    # ..........................................................................
    @property
    def events(self):
        '''
        A function to return the list of events that this subscriber accepts.
        '''
        return self._events

    def add_event(self, event):
        '''
        Adds another event to the list that this subscriber accepts.
        '''
        self._events.append(event)
        self._log.info('configured {:d} events for subscriber: {}.'.format(len(self._events), self._name))

    @events.setter
    def events(self, events):
        '''
        Sets the list of events that this subscriber accepts.
        '''
        self._events = events

    def print_events(self):
        if self._events:
            _events = []
            for event in self._events:
                _events.append('{} '.format(event.name))
            return ''.join(_events)
        else:
            return '(no filter)'

    # ..........................................................................
    def acceptable(self, message):
        '''
        A filter that returns True if the message has not yet been seen by
        this subscriber and its event is acceptable.
        '''
        if message.event in self._events:
            if message.acknowledged_by(self):
                self._log.info(self._color + 'message NOT ACCEPTABLE (already ackd): {}; event: {};'.format(message.name, message.event.description) \
                        + Fore.WHITE + Style.BRIGHT + '\t not acked? {}; acceptable event? {}'.format(not message.acknowledged_by(self), message.event in self._events))
                return True
            else:
                self._log.info(self._color + 'message ACCEPTABLE: {}; event: {};'.format(message.name, message.event.description) \
                        + Fore.WHITE + Style.BRIGHT + '\t not acked? {}; acceptable event? {}'.format(not message.acknowledged_by(self), message.event in self._events))
                return True
        else:
            self._log.info(self._color + 'message NOT ACCEPTABLE: {}; IGNORED by event: {};'.format(message.name, message.event.description) \
                    + Fore.WHITE + Style.BRIGHT + '\t not acked? {}; acceptable event? {}'.format(not message.acknowledged_by(self), message.event in self._events))
            return False

    # ................................................................
    def _republish_message(self, message):
        # put back into queue in case anyone else is interested
        if not message.fully_acknowledged:
            if self._message_bus.verbose:
                self._log.info(self._color + Style.DIM + 'returning unacknowledged message {} to queue;'.format(message.name) \
                        + Fore.WHITE + ' event: {}'.format(message.event.description))
            await self._message_bus.republish_message(message)
        else: # nobody wanted it
            if self._message_bus.verbose:
                self._log.info(self._color + Style.DIM + 'message {} acknowledged, awaiting garbage collection;'.format(message.name) \
                        + Fore.WHITE + ' event: {}'.format(message.event.description))
            # so we explicitly gc the message
            if not self._message_bus.garbage_collect(message):
                self._log.info(self._color + Style.DIM + 'message {} was not gc\'d so we republish...'.format(message.name))
                self._message_bus.republish_message(message)

    # ................................................................
    @final
    async def consume(self):
        '''
        Awaits a message on the message bus, then consumes it, filtering
        on event type, processing the message then putting it back on the
        bus to be further processed and eventually garbage collected.
        '''
        # 🍎 🍏 🍈 🍅 🍋 🍐 🍑 🥝 🥚 🥧 🧀
        _message = await self._message_bus.consume_message()
        self._message_bus.task_done()

        # if garbage collected, raise exception

        # if acceptable, consume

        # acknowledge we've seen it

        # if not fully-acknowledged, republish

        if _message.gcd:
            raise Exception('cannot consume: message has been garbage collected.')
        if self._message_bus.verbose:
            self._log.info(self._color + Style.DIM + 'consume message:' + Fore.WHITE + ' {}; event: {}'.format(_message.name, _message.event.description))

        if self.acceptable(_message):
            # this subscriber is interested and hasn't seen it before so handle the message
            if self._message_bus.verbose:
                self._log.info(self._color + Style.NORMAL + 'consuming acceptable message:' + Fore.WHITE + ' {}; event: {}'.format(_message.name, _message.event.description))
            # consume acceptable message
            asyncio.create_task(self._consume_message(_message))

            # acknowledge we've seen the message
            self._log.info(self._color + Style.NORMAL + 'ack message:' + Fore.WHITE + ' {}; event: {}'.format(_message.name, _message.event.description))
            _message.acknowledge(self)

            # republish if not fully acknowledged
            if not _message.fully_acknowledged:
                if self._message_bus.verbose:
                    self._log.info(self._color + Style.DIM + 'returning processed and now-acknowledged message {} to queue;'.format(_message.name) \
                            + Fore.WHITE + ' event: {}'.format(_message.event.description))
                self._message_bus.republish_message(_message)

        elif not _message.fully_acknowledged:
            self._log.info(self._color + Style.NORMAL + 'message was not acceptable, so republishing:' + Fore.WHITE \
                    + ' {}; event: {}'.format(_message.name, _message.event.description))
            self._republish_message(_message)

        else:
            self._log.info(self._color + Style.NORMAL + 'message was fully acknowledged, so NOT republishing:' + Fore.WHITE \
                    + ' {}; event: {}'.format(_message.name, _message.event.description))

    # ................................................................
    async def _consume_message(self, message):
        '''
        Kick off various tasks to process/consume the message. This creates
        tasks for process_message() followed by cleanup_message(). If the
        latter is overridden it should also called by the subclass method.

        :param message: the message to consume.
        '''
        if message.gcd:
            raise Exception('cannot _consume: message has been garbage collected.')
        if self._message_bus.verbose:
            self._log.info(self._color + 'consuming message:' + Fore.WHITE + ' {}; event: {}'.format(message.name, message.event.description))
        if message.gcd: # TEMP
            raise Exception('cannot _consume: message has been garbage collected.')
        _event = asyncio.Event()
        asyncio.create_task(self.process_message(message, _event))
        asyncio.create_task(self.cleanup_message(message, _event))
        results = await asyncio.gather(self._save(message), self._restart_host(message), return_exceptions=True)
        self._handle_results(results, message)
        _event.set()

    # ................................................................
    async def process_message(self, message, event):
        '''
        Process the message, i.e., do something with it to change the state of the robot.

        :param message:  the message to process.
        :param event:    the asyncio.Event to watch for message extention or cleaning up.
        '''
        while not event.is_set():
            if message.gcd: # TEMP
                raise Exception('cannot process: message has been garbage collected.')
            message.process(self)
            if self._message_bus.verbose:
                _elapsed_ms = (dt.now() - message.timestamp).total_seconds() * 1000.0
                self.print_message_info('processing message:', message, _elapsed_ms)
            # want to sleep for less than the deadline amount
            await asyncio.sleep(2)

    # ................................................................
    async def cleanup_message(self, message, event):
        '''
        Cleanup tasks related to completing work on a message.

        :param message:  consumed message that is done being processed.
        :param event:    the asyncio.Event to watch for message extention or cleaning up.
        '''
        # this will block until `event.set` is called
        await event.wait()
        # unhelpful simulation of i/o work
        await asyncio.sleep(random.random())
        if message.gcd: # TEMP
            raise Exception('cannot cleanup: message has been garbage collected.')
        message.expire()
        if self._message_bus.verbose:
            self._log.info(self._color + Style.DIM + 'cleanup done: acknowledged {}'.format(message.name))

    # ................................................................
    async def _save(self, message):
        '''
        Save message to a database.

        :param message:  consumed message to be saved.
        '''
        # unhelpful simulation of i/o work
        await asyncio.sleep(random.random())
        if random.randrange(1, 5) == 3:
            raise SaveFailed('Could not save {}'.format(message))
        if message.gcd: # TEMP
            raise Exception('cannot save: message has been garbage collected.')
        message.save()
        self._log.info(self._color + Style.DIM + 'saved {} into database.'.format(message.name))

    # ................................................................
    async def _restart_host(self, message):
        '''
        Restart a given host.

        Args:
            message (Message): consumed event message for a particular
                host to be restarted.
        '''
        # unhelpful simulation of i/o work
        await asyncio.sleep(random.random())
        if random.randrange(1, 5) == 3:
            raise RestartFailed('Could not restart {}'.format(message.hostname))
        if message.gcd: # TEMP
            raise Exception('cannot restart: message has been garbage collected.')
        message.restart()
        if self._message_bus.verbose:
            self._log.info(self._color + Style.DIM + 'restarted host {}; restarted? {}'.format(message.hostname, message.restarted))

    # ................................................................
    def _handle_results(self, results, message):
        if self._message_bus.verbose:
            self._log.info(self._color + 'handling results for message: {}'.format(message.name))
        for result in results:
            if isinstance(result, RestartFailed):
                self._log.error('retrying for failure to restart: {}'.format(message.hostname))
            elif isinstance(result, SaveFailed):
                self._log.error('failed to save: {}'.format(message.hostname))
            elif isinstance(result, Exception):
                self._log.error('handling general error: {}'.format(result))

    # ................................................................
    def get_formatted_time(self, label, value):
       if value is None:
           return ''
       elif value > 1000.0:
           return '\n' + LOG_INDENT + Fore.RED + label + '\t{:4.3f}s'.format(value/1000.0)
       else:
           return '\n' + LOG_INDENT + label + '\t{:4.3f}ms'.format(value)

    # ................................................................
    def print_message_info(self, info, message, elapsed):
        '''
        Print an informational string followed by details about the message.

        :param info:     the information string
        :param message:  the message to display
        :param elapsed:  the optional elapsed time (in milliseconds) for an operation
        '''
        self._log.info(self._color + info + '\n' \
                + LOG_INDENT + 'id:      \t' + Style.BRIGHT + '{}\n'.format(message.name) + Style.NORMAL \
                + LOG_INDENT + 'event:   \t' + Style.BRIGHT +  ( '{}\n'.format(message.event.description) if message.event else 'n/a: [gc\'d]\n' ) + Style.NORMAL \
                + LOG_INDENT + '{:d} procd;'.format(message.processed) + ' {:d} saved;'.format(message.saved) \
                        + ' {} restarted;'.format(message.restarted) + ' acked by: {}'.format(message.print_acks()) \
#               + LOG_INDENT + 'procd:   \t{:d}\n'.format(message.processed) \
#               + LOG_INDENT + 'saved:   \t{:d}\n'.format(message.saved) \
#               + LOG_INDENT + 'restart: \t{}\n'.format(message.restarted) \
#               + LOG_INDENT + 'ackd:    \t{}\n'.format(message.print_acks()) \
#               + LOG_INDENT + 'alive:   \t{:4.3f}ms'.format(message.age) \
                + self.get_formatted_time('alive:   ', message.age) \
                + self.get_formatted_time('elapsed: ', elapsed ))
#      + ( '\n' + LOG_INDENT + 'elapsed: \t{:4.3f}ms'.format(elapsed) if elapsed != None else '' ))

    # ..........................................................................
    @property
    def enabled(self):
        return self._enabled

    # ..........................................................................
    def enable(self):
        if not self._closed:
            if self._enabled:
                self._log.warning('already enabled.')
            else:
                self._enabled = True
                self._log.info('enabled.')
        else:
            self._log.warning('cannot enable: already closed.')

    # ..........................................................................
    def disable(self):
        if self._enabled:
            self._enabled = False
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


# GarbageCollector .............................................................
class GarbageCollector(Subscriber):
    '''
    Extends subscriber as a garbage collector that eliminates messages after
    they've passed the publish cycle.

    :param name:         the subscriber name (for logging)
    :param color:        the color to use for printing
    :param message_bus:  the message bus
    :param events:       the list of events used as a filter, None to set as cleanup task
    :param level:        the logging level
    '''
    def __init__(self, name, color, message_bus, level=Level.INFO):
        super().__init__(name, color, message_bus, level=Level.INFO)
        self._max_age = 3.0 # ms
        self._log.info(self._color + 'ready.')

    # ..........................................................................
    @property
    def is_gc(self):
        return True

    # ..........................................................................
    def acceptable(self, message):
        '''
        A filter that always returns True since this is the garbage collector.
        '''
        return True

    # ................................................................
    async def consume(self):
        '''
        Subscriber that garbage collects (destroys) an acknowledged message.
        '''
        _message = await self._message_bus.consume_message()
        self._log.info(self._color + Style.DIM + 'task done: message {}'.format(_message.name))
        self._log.info(self._color + Style.BRIGHT + 'CONSUME BEGIN: message {} ---------------------- '.format(_message.name))
        self._message_bus.task_done()

        # acknowledge we've seen the message
        _message.acknowledge(self)

        if self._message_bus.verbose:
            self._log.info(self._color + Style.DIM + 'gc-consuming message:' + Fore.WHITE + ' {}; event: {}; age: {:5.2f}ms'.format(\
                    _message.name, _message.event.description, _message.age))
        if not self.collect(_message):
            # was not cleaned up, expired nor acknowledged, so put back into queue
            if self._message_bus.verbose:
                self._log.info(self._color + Style.NORMAL + 'republishing unacknowledged message:' + Fore.WHITE \
                        + ' {}; event: {}'.format(_message.name, _message.event.description))
            self._message_bus.republish_message(_message)
        else:
            # otherwise "destroy" by not republishing
            if self._message_bus.verbose:
                self.print_message_info('destroying message:', _message, None)
        self._log.info(self._color + Style.BRIGHT + 'CONSUME END: message {} ---------------------- '.format(_message.name))

    # ................................................................
    def collect(self, message):
        '''
        Explicitly garbage collects the message, returning True if it was
        collected, False if it was neither expired nor fully-acknowledged.

        NOTE: Most of this function is simply a fancy log message - it
        could be significantly simplified if verbose is always set False.
        '''
        _info = None
        if self._message_bus.is_expired(message) and message.fully_acknowledged:
            _info = 'garbage collecting expired, fully-acknowledged message:'
        elif self._message_bus.is_expired(message):
            _info = 'garbage collecting expired message:'
        elif message.fully_acknowledged:
            _info = 'garbage collecting fully-acknowledged message:'
        if _info:
            if self._message_bus.verbose:
                self.print_message_info(_info, message, None)
            message.gc() # mark as garbage collected
            return True
        else:
            # not garbage collected
            return False

#EOF
