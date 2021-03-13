#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# Copyright 2020-2021 by Murray Altheim. All rights reserved. This file is part
# of the Robot Operating System project, released under the MIT License. Please
# see the LICENSE file included as part of this package.
#
# author:   Murray Altheim
# created:  2019-12-23
# modified: 2020-03-12
#
# Tasks that monitor other tasks using `asyncio`'s `Event` object - modified.
# 
# Notice! This requires:  attrs==19.1.0
# 
# See:          https://roguelynn.com/words/asyncio-true-concurrency/
# Source:       https://github.com/econchick/mayhem/blob/master/part-1/mayhem_10.py
# See also:     https://cheat.readthedocs.io/en/latest/python/asyncio.html
# And another:  https://codepr.github.io/posts/asyncio-pubsub/
#               https://gist.github.com/appeltel/fd3ddeeed6c330c7208502462639d2c9
#               https://www.oreilly.com/library/view/using-asyncio-in/9781492075325/ch04.html
# 
# unrelated:
# Python Style Guide: https://www.python.org/dev/peps/pep-0008/

#        1         2         3         4         5         6         7         8
#2345678901234567890123456789012345678901234567890123456789012345678901234567890

import asyncio, attr, itertools, signal, string, uuid
import random
import sys, time
from datetime import datetime as dt

from colorama import init, Fore, Style
init()

# ..............

from lib.logger import Logger, Level
#from lib.message_factory import MessageFactory
from lib.message import Message
from lib.async_message_bus import MessageBus
from lib.message_factory import MessageFactory
from lib.event import Event

# SaveFailed exception .........................................................
class SaveFailed(Exception):
    pass

# RestartFailed exception ......................................................
class RestartFailed(Exception):
    pass

# Publisher ....................................................................
class Publisher(object):
    def __init__(self, name, message_bus, message_factory, level=Level.INFO):
        '''
        Simulates a publisher of messages.

        :param message_bus:      the asynchronous message bus
        :param message_factory:  the factory for messages
        :param level:            the logging level
        '''
        self._log = Logger('pub-{}'.format(name), level)
        self._name = name
        if message_bus is None:
            raise ValueError('null message bus argument.')
        self._message_bus = message_bus
        if message_factory is None:
            raise ValueError('null message factory argument.')
        self._message_factory = message_factory
        self._log.info(Fore.BLACK + 'ready.')

    # ..........................................................................
    @property
    def name(self):
        return self._name

    # ................................................................
    async def publish(self):
        while True:
            _event = get_random_event()
            _message = self._message_factory.get_message(_event, _event.description)
            # publish the message
            self._message_bus.handle(_message)
            self._log.info(Fore.WHITE + Style.BRIGHT + 'PUBLISHED message: {} (event: {})'.format(_message, _event.description) \
                    + Fore.WHITE + ' ({:d} in queue)'.format(self._message_bus.queue_size))
            # simulate randomness of publishing messages
            await asyncio.sleep(random.random())
            self._log.debug(Fore.BLACK + Style.BRIGHT + 'after await sleep.')

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
        self._name = name
        self._color = color
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
        return event in [ Event.STOP, Event.INFRARED_PORT, Event.INFRARED_CNTR, Event.INFRARED_STBD, Event.BUMPER_PORT, Event.BUMPER_CNTR, Event.BUMPER_STBD ]

    # ................................................................
    async def consume(self, count):
        '''
        Consumer client to simulate subscribing to a publisher.
        This filters on event type, either consuming the message,
        ignoring it (and putting it back on the bus), or, if this
        is the cleanup task, destroying it.

        :param count:   the number of subscribers.
        '''
        # 🍈 🍅 🍐 🍑 🍓 🥝 🥚 🥧
#       _message = await queue.get()
        _message = await self._message_bus.consume_message()
        if not _message.expected:
            _message.expect(count-1) # we don't count cleanup task
        else:
            _message.acknowledge()
        self._log.info(self._color + '🍓 consuming message:' + Fore.WHITE + ' {}; event: {}'.format(_message, _message.event.description))

        if self._is_cleanup_task:
            if _message.fulfilled:
                _elapsed_ms = int((dt.now() - _message.timestamp).total_seconds() * 1000.0)
                if _message.event == Event.SNIFF:
                    self._log.info(self._color + Style.BRIGHT + 'CLEANUP message:' + Fore.WHITE + ' {}; event: {}'.format(_message, _message.event.description) \
                            + Fore.WHITE + Style.NORMAL + '; processed by {:d} in {:d}ms.'.format(_message.processed, _elapsed_ms))
                    if _message.event == Event.SNIFF and _message.processed < 2:
                        raise Exception('processed by only {:d}.'.format(_message.processed))
                else:
                    self._log.info(self._color + 'CLEANUP message:' + Fore.WHITE + ' {}; event: {}'.format(_message, _message.event.description) \
                            + Fore.WHITE + Style.NORMAL + '; processed by {:d} in {:d}ms.'.format(_message.processed, _elapsed_ms))
                # otherwise we exit to let it expire
                return
            elif self.acceptable(_message.event):
                raise Exception('🍏 UNPROCESSED acceptable message:' + Fore.WHITE + ' {}; event: {}'.format(_message, _message.event.description))
#               self._log.info(self._color + Style.BRIGHT + '🧀 RETURN unacknowledged message:' + Fore.WHITE + ' {}; event: {}'.format(_message, _message.event.description))
            # else put it back onto the bus

        else:
            # if this subscriber is interested, handle the message
            if self.accept(_message.event):
                self._log.info(self._color + Style.BRIGHT + 'CONSUMED message:' + Fore.WHITE + ' {}; event: {}'.format(_message, _message.event.description))
                # message processed, but not everyone has seen it yet so put back onto message bus once done
                asyncio.create_task(self._consume_message(_message))

        # was not cleaned up nor fulfilled, so put back into queue
        if not _message.fulfilled:
#           asyncio.create_task(queue.put(_message))
            await self._message_bus.publish_message(_message)
            self._log.info(self._color + Style.DIM + 'returning unprocessed message {} '.format(_message) + Fore.WHITE + ' to queue; event: {}'.format(_message.event.description))
        else:
            self._log.info(self._color + Style.DIM + '🍋 AWAITING CLEANUP message:' + Fore.WHITE + ' {}; event: {}'.format(_message, _message.event.description))

#        # if this subscriber is interested, consume the message
#        if self.accept(_message.event):
#            self._log.info(self._color + Style.BRIGHT + 'CONSUMED message:' + Fore.WHITE + ' {}; event: {}'.format(_message, _message.event.description))
#            # message processed, but not everyone has seen it yet so put back onto message bus once done
#            asyncio.create_task(self._consume_message(_message))
#        # if not fulfilled, put back into queue
#        if not _message.fulfilled:
# #          asyncio.create_task(queue.put(_message))
#            await self._message_bus.publish_message(_message)
#            self._log.info(self._color + Style.DIM + '🥚 returning unprocessed message {} '.format(_message) + Fore.WHITE + ' to queue; event: {}'.format(_message.event.description))
#        else:
#            self._log.info(self._color + Style.DIM + '🍋 AWAITING CLEANUP message:' + Fore.WHITE + ' {}; event: {}'.format(_message, _message.event.description))


    # ................................................................
    async def _consume_message(self, message):
        '''
        Kick off tasks to consume the message.

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
            message.processed += 1
            _elapsed_ms = int((dt.now() - message.timestamp).total_seconds() * 1000.0)
            self._log.info(Fore.GREEN + Style.NORMAL + 'processing message: {} in {:d}ms'.format(message, _elapsed_ms))
            # want to sleep for less than the deadline amount
            await asyncio.sleep(2)

    # ................................................................
    async def _cleanup(self, message, event):
        '''
        Cleanup tasks related to completing work on a message.

        :param message:  consumed message that is done being processed.
        :param event:    the asyncio.Event to watch for message extention or cleaning up.
        '''
        # this will block the rest of the coro until `event.set` is called
        await event.wait()
        # unhelpful simulation of i/o work
        await asyncio.sleep(random.random())
        message.acked == 0
        self._log.info(self._color + Style.DIM + 'done: acked {}'.format(message))

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

# ..........................................................................
EVENT_TYPES = [ Event.STOP, \
          Event.INFRARED_PORT, Event.INFRARED_CNTR, Event.INFRARED_STBD, \
          Event.BUMPER_PORT, Event.BUMPER_CNTR, Event.BUMPER_STBD, \
          Event.SNIFF, \
          Event.FULL_AHEAD, Event.ROAM, Event.ASTERN ] # not handled

def get_random_event():
    '''
    Returns one of the randomly-assigned event types.
    '''
    return EVENT_TYPES[random.randint(0, len(EVENT_TYPES)-1)]

# main .........................................................................
def main():

    _log = Logger("main", Level.INFO)
    _log.info(Fore.BLUE + '1. configuring test...')
    _loop = asyncio.get_event_loop()

    _message_bus = MessageBus(_loop, Level.INFO)
    _message_factory = MessageFactory(Level.INFO)
    _publisher1  = Publisher('1', _message_bus, _message_factory, Level.INFO)
#   _publisher2  = Publisher('2', _message_bus, _message_factory, Level.INFO)

    _subscriber1 = Subscriber('1-stop', Fore.YELLOW, _message_bus, [ Event.STOP, Event.SNIFF ], Level.INFO) # reacts to STOP
    _message_bus.add_subscriber(_subscriber1)
    _subscriber2 = Subscriber('2-infrared', Fore.MAGENTA, _message_bus, [ Event.INFRARED_PORT, Event.INFRARED_CNTR, Event.INFRARED_STBD ], Level.INFO) # reacts to IR
    _message_bus.add_subscriber(_subscriber2)
    _subscriber3 = Subscriber('3-bumper', Fore.GREEN, _message_bus, [ Event.SNIFF, Event.BUMPER_PORT, Event.BUMPER_CNTR, Event.BUMPER_STBD ], Level.INFO) # reacts to bumpers
    _message_bus.add_subscriber(_subscriber3)
    _subscriber4 = Subscriber('4-clean', Fore.RED, _message_bus, None, Level.INFO)
    _message_bus.add_subscriber(_subscriber4)

    try:
        _log.info(Fore.BLUE + '2. creating tasks for publishers...')
        _loop.create_task(_publisher1.publish())
#       _loop.create_task(_publisher2.publish())

        _log.info(Fore.BLUE + '3. creating task for subscribers...' + Style.RESET_ALL)
        _loop.create_task(_message_bus.consume())

        _log.info(Fore.BLUE + 'z. run forever...' + Style.RESET_ALL)
        _loop.run_forever()

    except KeyboardInterrupt:
        _log.info("process interrupted")
    finally:
        _loop.close()
        _log.info("successfully shutdown the message bus service.")


# ........................
if __name__ == "__main__":
    main()

