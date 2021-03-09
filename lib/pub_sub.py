#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# Copyright 2020-2021 by Murray Altheim. All rights reserved. This file is part
# of the Robot Operating System project, released under the MIT License. Please
# see the LICENSE file included as part of this package.
#
# author:   Murray Altheim
# created:  2021-02-24
# modified: 2021-03-01
#
# Contains the MessageBus, Subscription, Subscriber, and Publisher classes.
#
# see: https://www.aeracode.org/2018/02/19/python-async-simplified/
#

import asyncio, itertools, traceback
from abc import ABC, abstractmethod
import uuid
import random
from collections import deque as Deque
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
    async def publish_to_bus(self, message: Message):
        '''
        Publishes the Message to all Subscribers.
        '''
        self._log.info(Style.BRIGHT + 'publish message: eid: {}; event: {}'.format(message.eid, message.event.name))
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
    that subscribe to the MessageBus.
    '''
    def __init__(self, name, message_bus, event_types, level=Level.WARN):
        self._log = Logger('subscriber-{}'.format(name), level)
        self._name = name
        self._event_types = event_types
        self._log.debug('Subscriber created.')
        self._message_bus = message_bus
        self._processed = 0
        _queue_limit = 10
        self._deque = Deque([], maxlen=_queue_limit)
        self._log.debug('ready.')

    # ..............................................................................
    @property
    def name(self):
        return self._name

    # ..............................................................................
    @property
    def processed(self):
        return self._processed

    # ..............................................................................
    def queue_peek(self):
        '''
        Returns a peek at the last Message of the queue or None if empty.
        '''
        return self._deque[-1] if self._deque else None

    # ..............................................................................
    @property
    def queue_length(self):
        return len(self._deque)

    # ..............................................................................
    def print_queue_contents(self):
        str_list = []
        for _message in self._deque: 
            str_list.append('\n    msg#{}/{}/{}'.format(_message.number, _message.eid, _message.event.name))
        return ''.join(str_list)

    # ..............................................................................
    def filter(self, message):
        '''
        If the event type of the message is one of those within the event types
        we're interested in, return the message; otherwise return None.
        '''
        if message.event in self._event_types:
            self._log.debug(Fore.GREEN + 'FILTER-PASS   Subscriber.filter(): {} rxd msg #{}: priority: {}; desc: "{}"; VALUE: '.format(\
                    self._name, message.number, message.priority, message.description) + Fore.WHITE + Style.NORMAL + '{}'.format(message.value))
            return message
        else:
            self._log.debug(Fore.RED   + 'FILTER-IGNORE Subscriber.filter(): event: {}'.format(message.event.name))
            return None

    # ..............................................................................
    def receive_message(self, message):
        '''
        Receives a message obtained from a Subscription to the MessageBus,
        performing an actions based on receipt.

        This is to be subclassed to provide additional message handling or
        processing functionality.
        '''
        _message = self.filter(message)
        if _message:
            self._deque.appendleft(_message)
            self._log.info(Fore.GREEN + 'FILTER-PASS:  Subscriber.receive_message(): {} rxd msg #{}: priority: {}; desc: "{}"; VALUE: '.format(\
                    self._name, message.number, message.priority, message.description) + Fore.WHITE + Style.NORMAL + '{} .'.format(_message.value))
        else:
            self._log.info(Fore.RED   + 'FILTERED-OUT: Subscriber.receive_message() event: {}'.format(message.event.name))
        return _message

    # ..............................................................................
    def process_queue(self):
        '''
        Pops the queue of any messages, calling handle_message() for any.
        '''
        _peeked = self.queue_peek()
        if _peeked: # queue was not empty
            self._log.debug(Fore.WHITE + 'TICK! {:d} in queue.'.format(len(self._deque)))
            # we're only interested in INFRARED event types
            if _peeked.event is Event.INFRARED_PORT or _peeked.event is Event.INFRARED_STBD:
                _message = self._deque.pop()
                self._log.info(Fore.WHITE + 'MESSAGE POPPED:    {} rxd msg #{}: priority: {}; desc: "{}"; VALUE: '.format(\
                        self._name, _message.number, _message.priority, _message.description) + Fore.WHITE + Style.NORMAL + '{}'.format(_message.value))
#               time.sleep(3.0)
                self.handle_message(_message)
                self._log.info(Fore.WHITE + Style.BRIGHT + 'MESSAGE PROCESSED: {} rxd msg #{}: priority: {}; desc: "{}"; VALUE: '.format(\
                        self._name, _message.number, _message.priority, _message.description) + Fore.WHITE + Style.NORMAL + '{}'.format(_message.value))
            else: # did not expect anything except those two
                _message = self._deque.pop()
                raise Exception('did not expect MESSAGE to be passed: {}'.format(_message.event.name))
        else:
            self._log.debug(Style.DIM + 'TICK! {:d} in empty queue.'.format(len(self._deque)))

    # ..............................................................................
    @abstractmethod
    def handle_message(self, message):
        '''
        The abstract function that in a subclass would handle further processing
        of an incoming, filtered message.
        '''
        self._processed += 1
        self._log.info(Fore.YELLOW + Style.DIM + 'handle_message: msg #{}'.format(message.eid))
        pass

    # ..............................................................................
    @abstractmethod
    def subscribe(self):
        '''
        DESCRIPTION.
        '''
        self._log.debug('subscribe called.')
#       await asyncio.sleep(random.random() * 8)
        self._log.info(Fore.GREEN + 'Subscriber {} has subscribed.'.format(self._name))
    
        _message_count = 0
        _message = Message(-1, Event.NO_ACTION, None) # initial non-null message
        with Subscription(self._message_bus) as queue:
            while _message.event != Event.SHUTDOWN:
                _message = queue.get()
#               _message = await queue.get()
#               self._log.info(Fore.GREEN + '1. calling receive_message()...')
#               await self.receive_message(_message)
                self.receive_message(_message)
#               self._log.info(Fore.GREEN + '2. called receive_message(), awaiting..')
                _message_count += 1
                self._log.info(Fore.GREEN + 'Subscriber {} rxd msg #{}: priority: {}; desc: "{}"; VALUE: '.format(\
                        self._name, _message.number, _message.priority, _message.description) + Fore.WHITE + Style.NORMAL + '{}'.format(_message.value))
                if random.random() < 0.1:
                    self._log.info(Fore.GREEN + 'Subscriber {} has received enough'.format(self._name))
                    break
    
        self._log.info(Fore.GREEN + 'Subscriber {} is shutting down after receiving {:d} messages.'.format(self._name, _message_count))

# ..............................................................................
class Publisher(ABC):
    '''
    Abstract publisher, subclassed by any classes that intend to publish
    Messages to a MessageBus.
    '''
    def __init__(self, message_factory, message_bus, level=Level.INFO):
        self._log = Logger('pub', level)
        self._log.info(Fore.MAGENTA + 'Publisher: create.')
        self._message_factory = message_factory
        self._message_bus = message_bus
        self._counter = itertools.count()
        self._log.debug('ready.')

    # ..........................................................................
    @abstractmethod
    async def publish(self, iterations):
        '''
        TEMPORARY.
        Over the specified number of iterations, each publishing a random set of messages
        to the available subscriptions, shutting down once all have been completed.
        '''
        self._log.info(Fore.MAGENTA + Style.BRIGHT + 'Publish called.')
        for x in range(iterations):
            self._log.info(Fore.MAGENTA + 'Publisher: I have {} subscribers now'.format(len(self._message_bus.subscriptions)))
            _uuid = str(uuid.uuid4())
            _message = self.get_message_of_type(self.get_random_event_type(), 'msg_{:d}-{}'.format(x, _uuid))
            _message.number = next(self._counter)
            self._message_bus.publish_to_bus(_message)
            await asyncio.sleep(0.1)
    
        _shutdown_message = self.get_message_of_type(Event.SHUTDOWN, 'shutdown')
        self._message_bus.publish_to_bus(_shutdown_message)
        await asyncio.sleep(0.1)

    # ..........................................................................
    def get_message_of_type(self, event, value):
        '''
        Provided an Event type and a message value, returns a Message
        generated from the MessageFactory.
        '''
        return self._message_factory.get_message(event, value)

    def get_random_event_type(self):
        '''
        TEMPORARY.
        '''
        types = [ Event.STOP, \
            Event.FULL_AHEAD, \
            Event.ROAM, \
            Event.HIGH_TEMPERATURE, \
            Event.BATTERY_LOW, \
            Event.COLLISION_DETECT, \
            Event.BUMPER_PORT, \
            Event.BUMPER_CNTR, \
            Event.BUMPER_STBD, \
            Event.INFRARED_PORT_SIDE, \
            Event.INFRARED_PORT, \
            Event.INFRARED_CNTR, \
            Event.INFRARED_STBD, \
            Event.INFRARED_STBD_SIDE, \
            Event.MOTION_DETECT, \
            Event.EVENT_R1 ]
        return types[random.randint(0, len(types)-1)]

#EOF
