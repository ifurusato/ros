#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# Copyright 2021 by Murray Altheim. All rights reserved. This file is part of
# the Robot Operating System project and is released under the "Apache Licence, 
# Version 2.0". Please see the LICENSE file included as part of this package.
#
# author:   Murray Altheim
# created:  2021-02-24
# modified: 2021-02-24
#
# see: https://www.aeracode.org/2018/02/19/python-async-simplified/

import sys, time, asyncio, itertools, traceback
from abc import ABC, abstractmethod
from collections import deque as Deque
import uuid
import random
from colorama import init, Fore, Style
init()

from lib.event import Event
from lib.ticker import Ticker
from lib.message import Message
from lib.message_factory import MessageFactory
from lib.logger import Logger, Level
from lib.pub_sub import MessageBus, Publisher, Subscriber

# ..............................................................................
class MySubscriber(Subscriber):
    '''
    Extends Subscriber as a typical subscriber use case class.
    '''
    def __init__(self, name, ticker, message_bus, level=Level.INFO):
        super().__init__(name, message_bus, level)
        self._log.info(Fore.YELLOW + 'MySubscriber-{}: create.'.format(name))
        self._ticker = ticker
        self._ticker.add_callback(self.tick)
        self._discard_ignored = True
        _queue_limit = 10
        self._deque = Deque([], maxlen=_queue_limit)
        self._log.debug('ready.')

    # ..............................................................................
    def queue_peek(self):
        '''
        Returns a peek at the last Message of the queue or None if empty.
        '''
        return self._deque[-1] if self._deque else None

    # ..............................................................................
    def queue_length(self):
        return len(self._deque)

    # ..............................................................................
    def print_queue_contents(self):
        str_list = []
        for _message in self._deque: 
            str_list.append('\n    msg#{}/{}/{}'.format(_message.number, _message.eid, _message.event.name))
        return ''.join(str_list)

    # ..............................................................................
    def tick(self):
        '''
        Callback from the Ticker, used to pop the queue of any messages.
        '''
        _peek = self.queue_peek()

        if _peek: # queue was not empty
            self._log.debug(Fore.WHITE + 'TICK! {:d} in queue.'.format(len(self._deque)))
            # we're only interested in types Event.INFRARED_PORT or Event.INFRARED_CNTR
            if _peek.event is Event.INFRARED_PORT or _peek.event is Event.INFRARED_STBD:
                _message = self._deque.pop()
                self._log.info(Fore.WHITE + 'MESSAGE POPPED:    {} rxd msg #{}: priority: {}; desc: "{}"; value: '.format(\
                        self._name, _message.number, _message.priority, _message.description) + Fore.WHITE + Style.NORMAL + '{}'.format(_message.value))
                time.sleep(3.0)
                self._log.info(Fore.WHITE + Style.BRIGHT + 'MESSAGE PROCESSED: {} rxd msg #{}: priority: {}; desc: "{}"; value: '.format(\
                        self._name, _message.number, _message.priority, _message.description) + Fore.WHITE + Style.NORMAL + '{}'.format(_message.value))
            else: # we're not interested
                if self._discard_ignored:
                    _message = self._deque.pop()
                    self._log.info(Fore.YELLOW + Style.DIM + 'MESSAGE discarded: {}'.format(_message.event.name))
                else:
                    self._log.info(Fore.YELLOW + Style.DIM + 'MESSAGE ignored: {}'.format(_peek.event.name))
        else:
            self._log.debug(Style.DIM + 'TICK! {:d} in empty queue.'.format(len(self._deque)))
        # queue

    # ..............................................................................
    def filter(self, message):
        '''
        '''
        return message if ( message.event is Event.INFRARED_PORT or message.event is Event.INFRARED_STBD ) else None

    # ..............................................................................
    def handle_message(self, message):
        '''
        Extends the superclass' method, with a substantial delay to test
        whether the call is synchronous or asynchronous.
        '''
        self._deque.appendleft(message)
        self._log.info(Fore.YELLOW + 'MySubscriber add to queue: {} rxd msg #{}: priority: {}; desc: "{}"; value: '.format(\
                self._name, message.number, message.priority, message.description) + Fore.WHITE + Style.NORMAL + '{}'.format(message.value) \
                + Style.BRIGHT + ' {} in queue.'.format(len(self._deque)))

    # ..............................................................................
    def subscribe(self):
        '''
        Subscribes to the MessageBus by passing the call to the superclass.
        '''
        self._log.debug(Fore.YELLOW + 'MySubscriber.subscribe() called.')
        return super().subscribe()

# ..............................................................................
class MyPublisher(Publisher):
    '''
    DESCRIPTION.
    '''
    def __init__(self, message_factory, message_bus, level=Level.INFO):
        super().__init__(message_factory, message_bus, level)
#       self._log = Logger('my-pub', level)
        self._message_bus = message_bus # probably not needed
        self._log.info('ready.')

    # ..........................................................................
    def publish(self, iterations):
        '''
        DESCRIPTION.
        '''
        self._log.info(Fore.MAGENTA + Style.BRIGHT + 'MyPublish called, passing... ========= ======= ======== ======= ======== ')
        return super().publish(iterations)

# main .........................................................................
#_log = Logger('main', Level.INFO)

def main(argv):

    _log = Logger("main", Level.INFO)
    try:

        _log.info(Fore.BLUE + 'configuring objects...')
        _loop_freq_hz = 10
        _ticker = Ticker(_loop_freq_hz, Level.INFO)
        _message_factory = MessageFactory(Level.INFO)
        _message_bus = MessageBus()

#       _publisher = Publisher(_message_bus)
        _publisher = MyPublisher(_message_factory, _message_bus)
#       _publisher.enable()

        _publish = _publisher.publish(10)

        _log.info(Fore.BLUE + 'generating subscribers...')

        _subscribers = []
        _subscriptions = []
        for x in range(10):
            _subscriber = MySubscriber('s{}'.format(x), _ticker, _message_bus)
            _subscribers.append(_subscriber)
            _subscriptions.append(_subscriber.subscribe())

        _ticker.enable()
        loop = asyncio.get_event_loop()
        _log.info(Fore.BLUE + 'starting loop...')

        loop.run_until_complete(asyncio.gather(_publish, *_subscriptions))

        _log.info(Fore.BLUE + 'closing {} subscribers...'.format(len(_subscribers)))
        for subscriber in _subscribers:
            _log.info(Fore.BLUE + 'subscriber {} has {:d} messages remaining in queue: {}'.format(subscriber.name, subscriber.queue_length(), _subscriber.print_queue_contents()))

        _log.info(Fore.BLUE + 'loop complete.')

    except KeyboardInterrupt:
        _log.info('caught Ctrl-C; exiting...')
    except Exception:
        _log.error('error processing message bus: {}'.format(traceback.format_exc()))
    finally:
        _log.info('exit.')

# call main ....................................................................
if __name__== "__main__":
    main(sys.argv[1:])

#EOF
