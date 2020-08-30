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

from flask import jsonify
import queue, itertools
from colorama import init, Fore, Style
init()

from .message import Message
from .event import Event
from .enums import ActionState
from .logger import Logger, Level

# ..............................................................................
class MessageQueue():
    '''
        A priority message queue, where the highest priority is the lowest priority number.
    '''

    MAX_SIZE = 100

    def __init__(self, level):
        super().__init__()
        self._log = Logger('queue', level)
        self._log.debug('initialised MessageQueue...')
        heap = []
        self._counter = itertools.count()
        self._queue = queue.PriorityQueue(MessageQueue.MAX_SIZE)
        self._consumers = []
        self._log.info('MessageQueue ready.')

    # ......................................................
    def get_queue(self):
        '''
            Return the backing queue.
        '''
        return self._queue

    # ..........................................................................
    def add_consumer(self, consumer):
        '''
            Add a consumer to the optional list of message consumers.
        '''
        return self._consumers.append(consumer)

    # ..........................................................................
    def add(self, message):
        '''
            Add a new Message to the queue, then additionally to any consumers.
        '''
        self._queue.put(message);
        message.set_number(next(self._counter))
        self._log.debug('added message #{} to queue: priority {}: {}'.format(message.get_number(), message.get_priority(), message.get_description()))
        # we're finished, now add to any consumers
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
        self._log.debug('returning message: {} of priority {}.'.format(message.get_description(), message.get_priority()))
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
                self._log.debug('adding message {} of priority {} to returned list...'.format(message.get_description(), message.get_priority()))
                messages.append(message)
        except Empty:
            pass
        self._log.debug('returning {} messages.'.format(len(messages)))
        return messages

    # ......................................................
    def respond(self, event):
        '''
            Responds to the Event by wrapping it in Message and adding it to the backing queue.
        '''
        self._log.info('RESPOND to event {}.'.format(event.name))
        _message = Message(event)
        self.add(_message)
        return jsonify( [ { 'id': _message.get_number() }, { 'event': event.name }, { 'priority': event.priority } ] )

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
