#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# Copyright 2021 by Murray Altheim. All rights reserved. This file is part of
# the Robot Operating System project and is released under the "Apache Licence, 
# Version 2.0". Please see the LICENSE file included as part of this package.
#
# author:   Murray Altheim
# created:  2021-02-24
# modified: 2021-02-28
#
# see: https://www.aeracode.org/2018/02/19/python-async-simplified/
#

import asyncio, itertools, traceback
from abc import ABC, abstractmethod
import uuid
import random
from colorama import init, Fore, Style
init()

from lib.event import Event
from lib.message import Message
#from lib.message_factory import MessageFactory
from lib.logger import Logger, Level

# ..............................................................................
class MessageBus():
    '''
    Message Bus description.
    '''
    def __init__(self, level=Level.INFO):
        self._log = Logger('bus', level)
        self._log.debug('initialised...')
        self._subscriptions = set()
        self._log.debug('ready.')

    # ..........................................................................
    @property
    def subscriptions(self):
        '''
        Return the current set of Subscriptions.
        '''
        return self._subscriptions

    # ..........................................................................
    def publish(self, message: Message):
        '''
        Publishes the Message to all Subscribers.
        '''
        self._log.info(Style.BRIGHT + 'publish message: {}'.format(message))
        for queue in self._subscriptions:
            queue.put_nowait(message)

# ..............................................................................
class Subscription():
    '''
    A subscription on the MessageBus.
    '''
    def __init__(self, message_bus, level=Level.WARN):
        self._log = Logger('subscription', level)
        self._log.debug('__init__')
        self._message_bus = message_bus
        self.queue = asyncio.Queue()

    def __enter__(self):
        self._log.debug('__enter__')
        self._message_bus._subscriptions.add(self.queue)
        return self.queue

    def __exit__(self, type, value, traceback):
        self._log.debug('__exit__')
        self._message_bus._subscriptions.remove(self.queue)

# ..............................................................................
class Subscriber(ABC):
    '''
    Abstract subscriber functionality, to be subclassed by any classes
    that subscribe to a MessageBus.
    '''
    def __init__(self, name, message_bus, level=Level.WARN):
        self._log = Logger('subscriber-{}'.format(name), level)
        self._name = name
        self._log.debug('Subscriber created.')
        self._message_bus = message_bus
        self._log.debug('ready.')

    # ..............................................................................
    @property
    def name(self):
        return self._name

    # ..............................................................................
    def filter(self, message):
        '''
        Abstract filter: if not overridden, the default is simply to pass the message.
        '''
        self._log.info(Fore.RED + 'FILTER Subscriber.filter(): {} rxd msg #{}: priority: {}; desc: "{}"; value: '.format(\
                self._name, message.number, message.priority, message.description) + Fore.WHITE + Style.NORMAL + '{}'.format(message.value))
        return message

    # ..............................................................................
    @abstractmethod
    async def handle_message(self, message):
        '''
        Abstract function that receives a message obtained from a Subscription
        to the MessageBus, performing an actions based on receipt.

        This is to be subclassed to provide message handling/processing functionality.
        '''
        _event = message.event
        _message = self.filter(message)
        if _message:
            self._log.info(Fore.GREEN + 'FILTER-PASS:  Subscriber.handle_message(): {} rxd msg #{}: priority: {}; desc: "{}"; value: '.format(\
                    self._name, message.number, message.priority, message.description) + Fore.WHITE + Style.NORMAL + '{} .'.format(_message.value))
        else:
            self._log.info(Fore.GREEN + Style.DIM + 'FILTERED-OUT: Subscriber.handle_message() event: {}'.format(_event.name))
        return _message

    # ..............................................................................
    @abstractmethod
    async def subscribe(self):
        '''
        DESCRIPTION.
        '''
        self._log.debug('subscribe called.')
        await asyncio.sleep(random.random() * 8)
        self._log.info(Fore.GREEN + 'Subscriber {} has subscribed.'.format(self._name))
    
        _message_count = 0
        _message = Message(-1, Event.NO_ACTION, None) # initial non-null message
        with Subscription(self._message_bus) as queue:
            while _message.event != Event.SHUTDOWN:
                _message = await queue.get()
#               self._log.info(Fore.GREEN + '1. calling handle_message()...')
                self.handle_message(_message)
#               self._log.info(Fore.GREEN + '2. called handle_message(), awaiting..')
                _message_count += 1
                self._log.info(Fore.GREEN + 'Subscriber {} rxd msg #{}: priority: {}; desc: "{}"; value: '.format(\
                        self._name, _message.number, _message.priority, _message.description) + Fore.WHITE + Style.NORMAL + '{}'.format(_message.value))
                if random.random() < 0.1:
                    self._log.info(Fore.GREEN + 'Subscriber {} has received enough'.format(self._name))
                    break
    
        self._log.info(Fore.GREEN + 'Subscriber {} is shutting down after receiving {:d} messages.'.format(self._name, _message_count))

# ..............................................................................
class Publisher(ABC):
    '''
    Abstract publisher, subclassed by any classes that publish to a MessageBus.
    '''
    def __init__(self, message_factory, message_bus, level=Level.INFO):
        self._log = Logger('pub', level)
        self._log.info(Fore.MAGENTA + 'Publisher: create.')
        self._message_factory = message_factory
        self._message_bus = message_bus
        self._counter = itertools.count()
        self._log.debug('ready.')

    # ..........................................................................
    def get_message_of_type(self, event, value):
        '''
        Provided an Event type and a message value, returns a Message
        generated from the MessageFactory.
        '''
        return self._message_factory.get_message(event, value)

    def get_random_event_type(self):
        types = [ Event.STOP, Event.INFRARED_PORT, Event.INFRARED_STBD, Event.FULL_AHEAD, Event.ROAM, Event.EVENT_R1 ]
        return types[random.randint(0, len(types)-1)]

    # ..........................................................................
    @abstractmethod
    async def publish(self, iterations):
        '''
        DESCRIPTION.
        '''
        self._log.info(Fore.MAGENTA + Style.BRIGHT + 'Publish called.')
        for x in range(iterations):
            self._log.info(Fore.MAGENTA + 'Publisher: I have {} subscribers now'.format(len(self._message_bus.subscriptions)))
            _uuid = str(uuid.uuid4())
            _message = self.get_message_of_type(self.get_random_event_type(), 'msg_{:d}-{}'.format(x, _uuid))
            _message.number = next(self._counter)
            self._message_bus.publish(_message)
            await asyncio.sleep(1)
    
        _shutdown_message = self.get_message_of_type(Event.SHUTDOWN, 'shutdown')
        self._message_bus.publish(_shutdown_message)

#EOF
