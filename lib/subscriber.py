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

    # ................................................................
    @final
    async def consume(self):
        '''
        Awaits a message on the message bus, then consumes it, filtering
        on event type, processing the message then putting it back on the
        bus to be further processed and eventually garbage collected.

        This is marked 'final' as we don't expect subclasses to override
        it but rather the functions it calls.
        '''
        _message = await self._message_bus.consume_message()
        self._message_bus.task_done()
        # if garbage collected, raise exception
        if _message.gcd:
            raise Exception('{} cannot consume: message has been garbage collected.'.format(self.name))
        # if acceptable, consume/handle the message
        if self.acceptable(_message):
            # this subscriber is interested and hasn't seen it before so handle the message
            if self._message_bus.verbose:
                self._log.info(self._color + Style.NORMAL + 'consuming acceptable message:' + Fore.WHITE + ' {}; event: {}'.format(_message.name, _message.event.description))
            # handle acceptable message
            asyncio.create_task(self.handle_message(_message))
        # If not gc'd, republish the message. If fully-ackd it will be ignored
        if not _message.gcd:
            await self._message_bus.republish_message(_message)

    # ..........................................................................
    def acceptable(self, message):
        '''
        A filter that returns True if the message has not yet been seen by
        this subscriber and its event type is acceptable.
        '''
        _acceptable_msg = message.event in self._events
        _ackd_by_self   = message.acknowledged_by(self)
        if _acceptable_msg:
            if _ackd_by_self:
                self._log.info(self._color + 'NOT ACCEPTABLE: {} (already ackd); event: {};'.format(message.name, message.event.description) \
                        + Fore.WHITE + Style.BRIGHT + '\t not acked? {}; acceptable event? {}'.format(not _ackd_by_self, _acceptable_msg))
                return False
            else:
                self._log.info(self._color + 'ACCEPTABLE: {}; event: {};'.format(message.name, message.event.description) \
                        + Fore.WHITE + Style.BRIGHT + '\t acked? {}; acceptable event? {}'.format(message.acknowledged_by(self), _acceptable_msg))
                return True
        else:
            self._log.info(self._color + 'NOT ACCEPTABLE: {} (ignored event: {});'.format(message.name, message.event.description) \
                    + Fore.WHITE + Style.BRIGHT + '\t not acked? {}; acceptable event? {}'.format(not _ackd_by_self, _acceptable_msg))
            return False

    # ................................................................
    async def handle_message(self, message):
        '''
        Kick off various tasks to consume (process) the message by first creating
        an asyncio event. Tasks are then created for process_message() followed
        by cleanup_message(). If the latter is overridden it should also called
        by the subclass method as it flags the message as expired. Once these
        tasks have been created the asyncio event flag is set, indicating that
        the message has been consumed.

        The message is acknowledged if this subscriber has subscribed to the
        message's event type and has not seen this message before, or if it
        is not subscribed to the event type (i.e., the message is ignored).
        We don't acknowledge more than once.

        :param message:  the message to consume.
        '''
        if message.gcd:
            raise Exception('cannot _consume: message has been garbage collected.')
        if self._message_bus.verbose:
            self._log.info(self._color + 'HANDLE_MESSAGE:' + Fore.WHITE + ' {}; event: {}'.format(message.name, message.event.description))

        # acknowledge we've seen the message
        self._log.info(self._color + Style.NORMAL + 'ack accepted message:' + Fore.WHITE + ' {}; event: {}'.format(message.name, message.event.description))
        message.acknowledge(self)

        _event = asyncio.Event()
        print(Fore.RED + 'BEGIN event tracking for message:' + Fore.WHITE + ' {}; for event: {}'.format(message.name, message.event.description))

        self._log.info(self._color + 'creating task for processing message:' + Fore.WHITE + ' {}; for event: {}'.format(message.name, message.event.description))
        asyncio.create_task(self.process_message(message, _event))
        self._log.info(self._color + 'creating task for cleanup after message:' + Fore.WHITE + ' {}; for event: {}'.format(message.name, message.event.description))
        asyncio.create_task(self.cleanup_message(message, _event))
        self._log.info(self._color + 'creating task for saving and restarting message:' + Fore.WHITE + ' {}; for event: {}'.format(message.name, message.event.description))
        results = await asyncio.gather(self._save(message), self._restart_host(message), return_exceptions=True)
        self._log.info(self._color + 'handling result from message:' + Fore.WHITE + ' {}; for event: {}'.format(message.name, message.event.description))
        self._handle_results(results, message)

        print(Fore.RED + 'END event tracking for message:' + Fore.WHITE + ' {}; for event: {}'.format(message.name, message.event.description))
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
        if message.gcd: # TEMP
            raise Exception('cannot restart: message has been garbage collected.')
        if random.randrange(1, 5) == 3:
            raise RestartFailed('Could not restart {}'.format(message.hostname))
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
    async def handle_message(self, message):
        '''
        Overrides the method on Subscriber to explicitly garbage collect the
        message.

        NOTE: Most of this function is simply a fancy log message - it
        could be significantly simplified if verbose is always set False.

        :param message:  the message to garbage collect.
        '''
        if self._message_bus.verbose: # TEMP
            self._log.info(self._color + Style.BRIGHT + 'HANDLE_MESSAGE_GC:' + Fore.WHITE + ' {}; event: {}'.format(message.name, message.event.description))
        # TODO: only garbage collect if appropriate
        if message.gcd:
            raise Exception('cannot garbage collect: message has already been garbage collected.')
        _info = None
        _collectable = True
        if self._message_bus.is_expired(message) and message.fully_acknowledged:
            _info = 'garbage collecting expired, fully-acknowledged message:'
        elif self._message_bus.is_expired(message):
            _info = 'garbage collecting expired message:'
        elif message.fully_acknowledged:
            _info = 'garbage collecting fully-acknowledged message:'
        else:
            _info = 'unknown status: garbage collector returning unprocessed message:'
            _collectable = False
        if self._message_bus.verbose:
            self.print_message_info(_info, message, None)
        if _collectable:
            message.gc() # mark as garbage collected

#EOF
