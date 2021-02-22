#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# Copyright 2020 by Murray Altheim. All rights reserved. This file is part of
# the Robot OS project and is released under the "Apache Licence, Version 2.0".
# Please see the LICENSE file included as part of this package.
#
# author:   Murray Altheim
# created:  2020-01-18
# modified: 2020-03-26
#
# https://github.com/python/cpython/blob/3.8/Lib/heapq.py
# https://docs.python.org/3/library/heapq.html

#from flask import jsonify
import queue, itertools
from queue import Empty
from colorama import init, Fore, Style
init()

from lib.message import Message
from lib.event import Event
from lib.enums import ActionState
from lib.logger import Logger, Level

# ..............................................................................
class MessageQueue():
    '''
    A priority message queue, where the highest priority is the lowest 
    priority number. Consumers are added to the MessageQueue to receive
    the priorised Message.

    The MessageBus parameter provides the source of Messages.
    '''

    MAX_SIZE = 100

    def __init__(self, message_bus, level):
        super().__init__()
        self._log = Logger('queue', level)
        self._log.debug('initialised MessageQueue...')
        self._counter = itertools.count()
        self._queue = queue.PriorityQueue(MessageQueue.MAX_SIZE)
        self._consumers = []
        self._message_bus = message_bus
        self._message_bus.add_handler(Message, self.handle)
        self._log.info('MessageQueue ready.')

    # ..........................................................................
    def add_consumer(self, consumer):
        '''
        Add a consumer to the optional list of message consumers.
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
    def handle(self, message):
        '''
        Handle an incoming Message by adding it to the queue, then additionally
        to any consumers.
        '''
        if ( message.event is Event.CLOCK_TICK or message.event is Event.CLOCK_TOCK ):
            return
        self._log.info(Fore.WHITE + 'received message eid#{}/msg#{}: priority {}: {}'.format(message.eid, message.number, message.priority, message.description))
        if self._queue.full():
            try:
                _dumped = self._queue.get()
                self._log.info('dumping old message eid#{}/msg#{}: {}'.format(_dumped.eid, _dumped.number, _dumped.description))
            except Empty:
                pass
        message.number = next(self._counter)
        self._queue.put(message);
        self._log.info('added message eid#{}/msg#{} to queue: priority {}: {}'.format(message.eid, message.number, message.priority, message.description))
        # add to any consumers
        for consumer in self._consumers:
            consumer.add(message);

    # ......................................................
    def empty(self):
        '''
        Returns true if the queue is empty.
        '''
        return self._queue.empty()

    # ......................................................
    def size(self):
        '''
        Returns the current size of the queue. This returns "the approximate size of the queue (not reliable!)"
        '''
        return self._queue.qsize()

    # ......................................................
    def next(self):
        '''
        Return the next highest priority message in the queue.
        '''
        try:
            message = self._queue.get()
        except Empty:
            pass
        self._log.info(Fore.BLACK + 'returning message: {} of priority {}; queue size: {:d}'.format(message.description, message.priority, self._queue.qsize()))
        return message

    # ......................................................
    def next_group(self, count):
        '''
        Returns a list of the highest priority messages on the queue, whose size is either
        the count or all the remaining messages if their number is less than the count.
        '''
        try:
            messages = []
            while len(messages) < count and not self._queue.empty():
                message = self._queue.get()
                self._log.debug('adding message {} of priority {} to returned list...'.format(message.description, message.priority))
                messages.append(message)
        except Empty:
            pass
        self._log.debug('returning {} messages.'.format(len(messages)))
        return messages

    # ......................................................
    def clear(self):
        '''
        Clears all messages from the queue.
        '''
        while not self._queue.empty():
            try:
                self._queue.get(False)
            except Empty:
                continue
            self._queue.task_done()

#EOF
