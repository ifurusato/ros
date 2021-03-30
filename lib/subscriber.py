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
from datetime import datetime as dt
from colorama import init, Fore, Style
init()

from lib.logger import Logger, Level
from lib.event import Event

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
    def __init__(self, name, color, message_bus, events, level=Level.INFO):
        self._log = Logger('sub-{}'.format(name), level)
        self._name        = name
        self._color       = color
        self._message_bus = message_bus
        self._events      = events # list of acceptable event types
        self._is_cleanup_task = events is None
        self._log.info(self._color + 'ready.')

    # ..........................................................................
    @property
    def name(self):
        return self._name

    # ..........................................................................
    def accept(self, event):
        '''
        An event filter that returns True if the subscriber should accept the event.
        '''
        return ( self._events is None ) or ( event in self._events )

    def acceptable(self, event):
        '''
        A filter that returns True if the event is acceptable.
        '''
        return event in self._events

    # ................................................................
    async def consume(self):
        '''
        Awaits a message on the message bus, then consumes it, filtering
        on event type, processing the message then putting it back on the
        bus to be further processed and eventually garbage collected.
        '''
        # 🍎 🍏 🍈 🍅 🍋 🍐 🍑 🥝 🥚 🥧 🧀
        _message = await self._message_bus.consume_message()
        _message.acknowledge(self)
        if self._message_bus.verbose:
            self._log.info(self._color + Style.DIM + 'consume message:' + Fore.WHITE + ' {}; event: {}'.format(_message.name, _message.event.description))
        if self.accept(_message.event):
            # this subscriber is interested so handle the message
            if self._message_bus.verbose:
                self._log.info(self._color + Style.BRIGHT + 'consumed message:' + Fore.WHITE + ' {}; event: {}'.format(_message.name, _message.event.description))
            # is acceptable so consume
            asyncio.create_task(self._consume_message(_message))
        # put back into queue in case anyone else is interested
        if not _message.acknowledged:
            if self._message_bus.verbose:
                self._log.info(self._color + Style.DIM + 'returning unacknowledged message {} to queue;'.format(_message.name) \
                        + Fore.WHITE + ' event: {}'.format(_message.event.description))
            self._message_bus.republish_message(_message)
        else: # nobody wanted it
            if self._message_bus.verbose:
                self._log.info(self._color + Style.DIM + 'message {} acknowledged, awaiting garbage collection;'.format(_message.name) \
                        + Fore.WHITE + ' event: {}'.format(_message.event.description))
            # so we explicitly gc the message
            if not self._message_bus.garbage_collect(_message):
                self._log.info(self._color + Style.DIM + 'message {} was not gc\'d so we republish...'.format(_message.name))
                self._message_bus.republish_message(_message)

    # ................................................................
    async def _consume_message(self, message):
        '''
        Kick off various tasks to process/consume the message.

        :param message: the message to consume.
        '''
        if self._message_bus.verbose:
            self._log.info(self._color + 'consuming message:' + Fore.WHITE + ' {}; event: {}'.format(message.name, message.event.description))
        _event = asyncio.Event()
        asyncio.create_task(self._process_message(message, _event))
        asyncio.create_task(self._cleanup_message(message, _event))
        results = await asyncio.gather(self._save(message), self._restart_host(message), return_exceptions=True)
        self._handle_results(results, message)
        _event.set()

    # ................................................................
    async def _process_message(self, message, event):
        '''
        Process the message, i.e., do something with it to change the state of the robot.

        :param message:  the message to process.
        :param event:    the asyncio.Event to watch for message extention or cleaning up.
        '''
        while not event.is_set():
            message.process()
            _elapsed_ms = (dt.now() - message.timestamp).total_seconds() * 1000.0
            if self._message_bus.verbose:
                self._log.info(self._color + Style.BRIGHT + 'processing message: {} (event: {}) in {:5.2f}ms'.format(message.name, message.event.description, _elapsed_ms))
            # want to sleep for less than the deadline amount
            await asyncio.sleep(2)

    # ................................................................
    async def _cleanup_message(self, message, event):
        '''
        Cleanup tasks related to completing work on a message.

        :param message:  consumed message that is done being processed.
        :param event:    the asyncio.Event to watch for message extention or cleaning up.
        '''
        # this will block until `event.set` is called
        await event.wait()
        # unhelpful simulation of i/o work
        await asyncio.sleep(random.random())
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
        super().__init__(name, color, message_bus, None, level=Level.INFO)
        self._max_age = 3.0 # ms
        self._log.info(self._color + 'ready.')

    # ................................................................
    def _get_acks(self, message):
        _list = []
        for subscriber in message.acknowledgements: 
            _list.append('{} '.format(subscriber.name))
        return ''.join(_list)

    # ................................................................
    def collect(self, message):
        '''
        Explicitly garbage collects the message, returning True if it was
        collected, False if it was neither expired nor fully-acknowledged.
        '''
        if self._message_bus.is_expired(message) and message.acknowledged:
            if self._message_bus.verbose:
                self._log.info(self._color + '🗑️  GARBAGE COLLECT expired, acknowledged message \'{}\' '.format(message.name) + Fore.WHITE \
                        + ' (event: {});'.format(message.event.description) \
                        + Fore.WHITE + Style.NORMAL + ' processed by {:d}; was alive for {:5.2f}ms;\n'.format(message.processed, message.age)
                        + '    ackd by: {}'.format(self._get_acks(message)))
            return True
        elif self._message_bus.is_expired(message):
            if self._message_bus.verbose:
                self._log.info(self._color + '🗑️  GARBAGE COLLECT expired message \'{}\' '.format(message.name) + Fore.WHITE \
                        + ' (event: {});'.format(message.event.description) \
                        + Fore.WHITE + Style.NORMAL + ' processed by {:d}; was alive for {:5.2f}ms;\n'.format(message.processed, message.age)
                        + '    ackd by: {}'.format(self._get_acks(message)))
            return True
        elif message.acknowledged:
            _elapsed_ms = (dt.now() - message.timestamp).total_seconds() * 1000.0
            if message.event == Event.SNIFF: # temporary check to see that SNIFF messages are processed twice
                if self._message_bus.verbose:
                    self._log.info(self._color + Style.BRIGHT + '🗑️  GARBAGE COLLECT SNIFF message \'{}\' '.format(message.name) \
                            + Fore.WHITE + ' (event: {});'.format(message.event.description) \
                            + Fore.WHITE + Style.NORMAL + ' processed by {:d}; was alive for {:5.2f}ms;\n'.format(message.processed, _elapsed_ms)
                            + '    ackd by: {}'.format(self._get_acks(message)))
                if message.event == Event.SNIFF and message.processed < 2:
                    raise Exception('message {} (event: {}) processed by only {:d}; ackd by: {}'.format(\
                            message.name, message.event, message.processed, self._get_acks(message)))
            else:
                if self._message_bus.verbose:
                    self._log.info(self._color + '🗑️  GARBAGE COLLECT acknowledged message \'{}\' '.format(message.name) + Fore.WHITE \
                            + ' (event: {});'.format(message.event.description) \
                            + Fore.WHITE + Style.NORMAL + ' processed by {:d}; was alive for {:5.2f}ms;\n'.format(message.processed, message.age)
                            + '    ackd by: {}'.format(self._get_acks(message)))
            return True
        else:
            # not garbage collected
            return False

    # ................................................................
    async def consume(self):
        '''
        Consumer client that garbage collects (destroys) an acknowledged message.
        '''
        _message = await self._message_bus.consume_message()
        _message.acknowledge(self)
        if self._message_bus.verbose:
            self._log.info(self._color + 'gc-consuming message:' + Fore.WHITE + ' {}; event: {}; age: {:5.2f}ms'.format(_message.name, _message.event.description, _message.age))
        if not self.collect(_message):
            # was not cleaned up, expired nor acknowledged, so put back into queue
            self._log.info(self._color + Style.NORMAL + 'republishing unacknowledged message:' + Fore.WHITE \
                    + ' {}; event: {}'.format(_message.name, _message.event.description))
            self._message_bus.republish_message(_message)

#EOF
