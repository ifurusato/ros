#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# Copyright 2020-2021 by Murray Altheim. All rights reserved. This file is part
# of the Robot Operating System project, released under the MIT License. Please
# see the LICENSE file included as part of this package.
#
# author:   Murray Altheim
# created:  2019-12-23
# modified: 2021-03-17
#

import asyncio
import random
from colorama import init, Fore, Style
init()

from lib.logger import Logger, Level
from lib.message import Message
from lib.event import Event

EVENT_TYPES = [ Event.STOP, \
          Event.INFRARED_PORT, Event.INFRARED_CNTR, Event.INFRARED_STBD, \
          Event.BUMPER_PORT, Event.BUMPER_CNTR, Event.BUMPER_STBD, \
          Event.FULL_AHEAD, Event.ROAM, Event.ASTERN, # not handled
          Event.SNIFF ]

# Publisher ....................................................................
class Publisher(object):
    '''
    Eventually this will be an abstract class.
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
        print(Fore.RED + 'NAME: {}  --------------------'.format(name) + Style.RESET_ALL)
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
            _event = self._get_random_event()
            _message = self._message_factory.get_message(_event, _event.description)
#           _message.set_subscribers(self._message_bus.subscribers)
            # publish the message
            self._message_bus.publish_message(_message)
            self._log.info(Fore.WHITE + Style.BRIGHT + '{} PUBLISHED message: {} (event: {})'.format(self.name, _message, _event.description))
            # simulate randomness of publishing messages
            await asyncio.sleep(random.random())
            self._log.debug(Fore.BLACK + Style.BRIGHT + 'after await sleep.')

    # ..........................................................................
    def _get_random_event(self):
        '''
        Returns one of the randomly-assigned event types.
        '''
        return EVENT_TYPES[random.randint(0, len(EVENT_TYPES)-1)]

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

#EOF
