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
# See:          https://roguelynn.com/words/asyncio-true-concurrency/
# Source:       https://github.com/econchick/mayhem/blob/master/part-1/mayhem_10.py
# See also:     https://cheat.readthedocs.io/en/latest/python/asyncio.html
# And another:  https://codepr.github.io/posts/asyncio-pubsub/
#               https://gist.github.com/appeltel/fd3ddeeed6c330c7208502462639d2c9
#               https://www.oreilly.com/library/view/using-asyncio-in/9781492075325/ch04.html
#
# unrelated:
# Python Style Guide: https://www.python.org/dev/peps/pep-0008/
#

import asyncio, itertools, signal, string, uuid
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

# Publisher ....................................................................
class Publisher(object):
    '''
    Eventually an abstract class.
    '''
    def __init__(self, name, message_bus, message_factory, level=Level.INFO):
        '''
        Simulates a publisher of messages.

        :param name:             the unique name for the publisher
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
        self._enabled    = False # by default
        self._closed     = False
        self._log.info(Fore.BLACK + 'ready.')

    # ..........................................................................
    @property
    def name(self):
        return self._name

    # ................................................................
    async def publish(self):
        '''
        Begins publication of messages. The MessageBus itself calls this function
        as part of its asynchronous loop; it shouldn't be called by anyone except
        the MessageBus.
        '''
        if self._enabled:
            self._log.warning('publish cycle already started.')
            return
        self._enabled = True
        while self._enabled:
            _event = get_random_event()
            _message = self._message_factory.get_message(_event, _event.description)
            _message.set_subscribers(self._message_bus.subscribers)
            # publish the message
            self._message_bus.publish_message(_message)
            self._log.info(Fore.WHITE + Style.BRIGHT + '{} PUBLISHED message: {} (event: {})'.format(self.name, _message, _event.description))
            # simulate randomness of publishing messages
            await asyncio.sleep(random.random())
            self._log.debug(Fore.BLACK + Style.BRIGHT + 'after await sleep.')

    # ..........................................................................
    @property
    def enabled(self):
        return self._enabled

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

# ..........................................................................
EVENT_TYPES = [ Event.STOP, \
#         Event.INFRARED_PORT, Event.INFRARED_CNTR, Event.INFRARED_STBD, \
#         Event.BUMPER_PORT, Event.BUMPER_CNTR, Event.BUMPER_STBD, \
#         Event.FULL_AHEAD, Event.ROAM, Event.ASTERN,
          Event.SNIFF ] # not handled

def get_random_event():
    '''
    Returns one of the randomly-assigned event types.
    '''
    return EVENT_TYPES[random.randint(0, len(EVENT_TYPES)-1)]

# main .........................................................................
def main():

    _log = Logger("main", Level.INFO)
    _log.info(Fore.BLUE + '1. configuring test...')

    _message_factory = MessageFactory(Level.INFO)

    _message_bus = MessageBus(Level.INFO)
    _publisher1  = Publisher('A', _message_bus, _message_factory, Level.INFO)
    _message_bus.register_publisher(_publisher1)
    _publisher2  = Publisher('B', _message_bus, _message_factory, Level.INFO)
    _message_bus.register_publisher(_publisher2)

    _subscriber1 = Subscriber('1-stop', Fore.YELLOW, _message_bus, [ Event.STOP, Event.SNIFF ], Level.INFO) # reacts to STOP
    _message_bus.register_subscriber(_subscriber1)
    _subscriber2 = Subscriber('2-infrared', Fore.MAGENTA, _message_bus, [ Event.INFRARED_PORT, Event.INFRARED_CNTR, Event.INFRARED_STBD ], Level.INFO) # reacts to IR
    _message_bus.register_subscriber(_subscriber2)
    _subscriber3 = Subscriber('3-bumper', Fore.GREEN, _message_bus, [ Event.SNIFF, Event.BUMPER_PORT, Event.BUMPER_CNTR, Event.BUMPER_STBD ], Level.INFO) # reacts to bumpers
    _message_bus.register_subscriber(_subscriber3)

    _message_bus.print_publishers()
    _message_bus.print_subscribers()
#   sys.exit(0)

    try:
        _message_bus.enable()
    except KeyboardInterrupt:
        _log.info('publish-subscribe interrupted')
    except Exception as e:
        _log.error('error in publish-subscribe: {}'.format(e))
    finally:
        _message_bus.close()
        _log.info('successfully shutdown the message bus service.')

# ........................
if __name__ == "__main__":
    main()

