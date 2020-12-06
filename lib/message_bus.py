#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# Copyright 2020 by Murray Altheim. All rights reserved. This file is part of
# the Robot OS project and is released under the "Apache Licence, Version 2.0".
# Please see the LICENSE file included as part of this package.
#
# author:   Murray Altheim
# created:  2020-11-05
# modified: 2020-11-05
#
# https://pypi.org/project/pymessagebus/
# https://github.com/DrBenton/pymessagebus
#

import sys, itertools, time, traceback
from colorama import init, Fore, Style
init()
try:
    from pymessagebus import MessageBus as PyMessageBus
except ImportError:
    sys.exit(Fore.RED + 'This script requires the pymessagebus module\nInstall with: sudo pip3 install "pymessagebus==1.*"' + Style.RESET_ALL)

from lib.message import Message
from lib.event import Event
from lib.logger import Logger, Level

# ..............................................................................
class MessageBus():
    '''
    A message bus wrapper around pymessagebus. This provides a simple
    centralised pub-sub-like framework for handling Message objects.
    '''

    MAX_SIZE = 100

    def __init__(self, level):
        super().__init__()
        self._log = Logger('bus', level)
        self._log.debug('initialised MessageQueue...')
        self._counter = itertools.count()
        self._message_bus = PyMessageBus()
        self._consumers = []
        self._log.info('ready.')

    # ..........................................................................
    def add_handler(self, message_type, handler):
        '''
        Add a handler to the message bus for the given message type.
        '''
        self._message_bus.add_handler(message_type, handler)
        self._log.info(Fore.YELLOW + 'added message handler \'{}()\' for type:\t{}'.format(handler.__name__, message_type.__name__))

    # ..........................................................................
    def add_consumer(self, consumer):
        '''
        Add a consumer to the optional list of message consumers.
        These are processed after the message handlers.
        '''
        return self._consumers.append(consumer)

    # ..........................................................................
    def remove_consumer(self, consumer):
        '''
        Remove the consumer from the list of message consumers.
        '''
        try:
            self._consumers.remove(consumer)
        except ValueError:
            self._log.warn('message consumer was not in list.')

    # ..........................................................................
    def handle(self, message: Message):
        '''
        Add a new Message to the bus, then additionally to any consumers.
        '''
#       self._log.info(Fore.BLACK + 'handle message eid#{}; priority={}; description: {}'.format(message.eid, message.priority, message.description))
        self._message_bus.handle(message)
#       if message.event is Event.CLOCK_TICK:
#           # add to any consumers
#           for consumer in self._consumers:
#               self._log.debug(Fore.BLACK + 'passing message: eid#{}; priority={}; description: {} to consumer: {}'.format(message.eid, message.priority, message.description, consumer))
#               consumer.add(message);
        for consumer in self._consumers:
            consumer.add(message);


    # ......................................................
    def empty(self):
        '''
            Returns true if the bus is empty.
        '''
        return None #self._queue.empty()

    # ......................................................
    def size(self):
        '''
            Returns the current size of the bus. This returns "the approximate size of the bus (not reliable!)"
        '''
        return 0 #self._queue.qsize()

    # ......................................................
    def next(self):
        '''
            Return the next highest priority message in the bus.
        '''
        try:
            message = None #self._queue.get()
        except Empty:
            pass
#       self._log.info(Fore.BLACK + 'returning message: {} of priority {}; bus size: {:d}'.format(message.description, message.priority, self._queue.qsize()))
        return message

    # ......................................................
    def clear(self):
        '''
            Clears all messages from the bus.
        '''
        pass
#       while not self._queue.empty():
#           try:
#               self._queue.get(False)
#           except Empty:
#               continue
#           self._queue.task_done()

#EOF
