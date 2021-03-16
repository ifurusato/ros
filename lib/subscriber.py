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
        _message.acknowledge(self.name)
        self._log.debug(self._color + 'consume message:' + Fore.WHITE + ' {}; event: {}'.format(_message, _message.event.description))
        if self.accept(_message.event):
            # this subscriber is interested so handle the message
            self._log.info(self._color + Style.BRIGHT + '🍎 consumed message:' + Fore.WHITE + ' {}; event: {}'.format(_message, _message.event.description))
            # is acceptable so consume
            asyncio.create_task(self._consume_message(_message))
        # put back into queue in case anyone else is interested
        if not _message.fulfilled:
            self._log.info(self._color + Style.DIM + 'returning unprocessed message {} to queue;'.format(_message) \
                    + Fore.WHITE + ' event: {}'.format(_message.event.description))
            self._message_bus.republish_message(_message)
        else: # nobody wanted it
            self._log.info(self._color + Style.DIM + '🍏 message {} fulfilled, awaiting garbage collection;'.format(_message) \
                    + Fore.WHITE + ' event: {}'.format(_message.event.description))

    # ................................................................
    async def _consume_message(self, message):
        '''
        Kick off various tasks to process/consume the message.

        :param message: the message to consume.
        '''
        _event = asyncio.Event()

        asyncio.create_task(self._process(message, _event))
        asyncio.create_task(self._cleanup(message, _event))
        results = await asyncio.gather(self._save(message), self._restart_host(message), return_exceptions=True)
        self._handle_results(results, message)

        _event.set()

    # ................................................................
    async def _process(self, message, event):
        '''
        Process the message, i.e., do something with it to change the state of the robot.

        :param message:  the message to process.
        :param event:    the asyncio.Event to watch for message extention or cleaning up.
        '''
        while not event.is_set():
            message.process()
            _elapsed_ms = int((dt.now() - message.timestamp).total_seconds() * 1000.0)
            self._log.info(Fore.GREEN + Style.BRIGHT + 'processing message: {} (event: {}) in {:d}ms'.format(message, message.event.description, _elapsed_ms))
            # want to sleep for less than the deadline amount
            await asyncio.sleep(2)

    # ................................................................
    async def _cleanup(self, message, event):
        '''
        Cleanup tasks related to completing work on a message.

        :param message:  consumed message that is done being processed.
        :param event:    the asyncio.Event to watch for message extention or cleaning up.
        '''
        # this will block until `event.set` is called
        await event.wait()
        # unhelpful simulation of i/o work
        await asyncio.sleep(random.random())
        message.expired == True
        self._log.debug(self._color + Style.DIM + 'done: acknowledged {}'.format(message))

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
        message.saved = True
        self._log.info(self._color + Style.DIM + 'saved {} into database.'.format(message))

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
        message.restart = True
        self._log.info(self._color + Style.DIM + 'restarted host {}'.format(message.hostname))

    # ................................................................
    def _handle_results(self, results, message):
        self._log.info('handling results for message: {}'.format(message))
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
        self._log.info(self._color + 'ready.')

    # ................................................................
    async def consume(self):
        '''
        Consumer client that garbage collects (destroys) a fulfilled message.
        '''
        _message = await self._message_bus.consume_message()
        _message.acknowledge(self.name)
        self._log.debug(self._color + '🗑️  consuming message:' + Fore.WHITE + ' {}; event: {}'.format(_message, _message.event.description))

        if _message.fulfilled:
            _elapsed_ms = int((dt.now() - _message.timestamp).total_seconds() * 1000.0)
            if _message.event == Event.SNIFF:
                self._log.info(self._color + Style.BRIGHT + '🗑️  garbage collect SNIFF message \'{}\' '.format(_message.name) \
                        + Fore.WHITE + ' (event: {});'.format(_message.event.description) \
                        + Fore.WHITE + Style.NORMAL + ' processed by {:d}; was alive for {:d}ms;\n'.format(_message.processed, _elapsed_ms)
                        + '    ackd by: {}'.format(_message.acknowledgements))
                if _message.event == Event.SNIFF and _message.processed < 2:
                    raise Exception('message {} (event: {}) processed by only {:d}; ackd by: {}'.format(\
                            _message.name, _message.event, _message.processed, _message.acknowledgements))
            else:
                self._log.info(self._color + '🗑️  garbage collect message \'{}\' '.format(_message.name) + Fore.WHITE \
                        + ' (event: {});'.format(_message.event.description) \
                        + Fore.WHITE + Style.NORMAL + ' processed by {:d}; was alive for {:d}ms;\n'.format(_message.processed, _elapsed_ms)
                        + '    ackd by: {}'.format(_message.acknowledgements))
            # now we exit to let it expire
        else:
            # was not cleaned up nor fulfilled, so put back into queue
            self._log.warning(self._color + Style.BRIGHT + '🧀 republishing unfulfilled message:' + Fore.WHITE \
                    + ' {}; event: {}'.format(_message, _message.event.description))
            self._message_bus.republish_message(_message)

#EOF
