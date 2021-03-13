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

import asyncio, attr, itertools, signal, string, uuid
import random
import sys, time
from datetime import datetime as dt

from colorama import init, Fore, Style
init()

from lib.logger import Logger, Level
from lib.message import Message
from lib.async_message_bus import MessageBus
from lib.message_factory import MessageFactory
from lib.subscriber import Subscriber
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
            self._message_bus.publish_message(_message)
            self._log.info(Fore.WHITE + Style.BRIGHT + '{} PUBLISHED message: {} (event: {})'.format(self.name, _message, _event.description))
            # simulate randomness of publishing messages
            await asyncio.sleep(random.random())
            self._log.debug(Fore.BLACK + Style.BRIGHT + 'after await sleep.')

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
    _publisher1  = Publisher('A', _message_bus, _message_factory, Level.INFO)
    _publisher2  = Publisher('B', _message_bus, _message_factory, Level.INFO)

    _subscriber1 = Subscriber('1-stop', Fore.YELLOW, _message_bus, [ Event.STOP, Event.SNIFF ], Level.INFO) # reacts to STOP
    _message_bus.add_subscriber(_subscriber1)
    _subscriber2 = Subscriber('2-infrared', Fore.MAGENTA, _message_bus, [ Event.INFRARED_PORT, Event.INFRARED_CNTR, Event.INFRARED_STBD ], Level.INFO) # reacts to IR
    _message_bus.add_subscriber(_subscriber2)
    _subscriber3 = Subscriber('3-bumper', Fore.GREEN, _message_bus, [ Event.SNIFF, Event.BUMPER_PORT, Event.BUMPER_CNTR, Event.BUMPER_STBD ], Level.INFO) # reacts to bumpers
    _message_bus.add_subscriber(_subscriber3)

#   _subscriber4 = GarbageCollector('4-clean', Fore.RED, _message_bus, Level.INFO)
#   _message_bus.add_subscriber(_subscriber4)
    _message_bus.print_subscribers()

    try:
        _log.info(Fore.BLUE + '2. creating tasks for publishers...')
        _loop.create_task(_publisher1.publish())
        _loop.create_task(_publisher2.publish())

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

