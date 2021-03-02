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
# see: https://www.aeracode.org/2018/02/19/python-async-simplified/

import sys, time, asyncio, itertools, traceback
from abc import ABC, abstractmethod
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

#from lib.ifs import IntegratedFrontSensor
from mock.ifs import MockIntegratedFrontSensor

# ..............................................................................
class MySubscriber(Subscriber):
    '''
    Extends Subscriber as a typical subscriber use case class.
    '''
    def __init__(self, name, ticker, message_bus, event_types, level=Level.INFO):
        super().__init__(name, message_bus, event_types, level)
        self._log.info(Fore.YELLOW + 'MySubscriber-{}: create.'.format(name))
        self._ticker = ticker
        self._ticker.add_callback(self.process_queue)
        self._log.debug('ready.')

    # ..............................................................................
    def handle_message(self, message):
        '''
        Extends the superclass' method for processing an incoming, filtered message,
        doing nothing in this case.
        '''
        self._log.info(Fore.YELLOW + 'add: {} msg #{}: prior: {}; desc: "{}"; value: '.format(\
                self._name, message.number, message.priority, message.description) + Fore.WHITE + Style.NORMAL + '{}'.format(message.value) \
                + Style.BRIGHT + ' {} in queue.'.format(self.queue_length))
        return super().handle_message(message)

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

        _log.info('creating clock...')
        _log.info('creating integrated front sensor...')
#       _ifs = IntegratedFrontSensor(_config, _clock, Level.INFO)
        _ifs = MockIntegratedFrontSensor(_message_bus, Level.INFO)
        _ifs.enable()

        _publish = _publisher.publish(10)

        _log.info(Fore.BLUE + 'generating subscribers...')

        # types = [ Event.STOP, Event.INFRARED_PORT, Event.INFRARED_STBD, Event.FULL_AHEAD, Event.ROAM, Event.EVENT_R1 ]
        _event_types = [ Event.INFRARED_PORT, Event.INFRARED_STBD ]
        _subscribers = []
        _subscriptions = []
        for x in range(10):
            _subscriber = MySubscriber('s{}'.format(x), _ticker, _message_bus, _event_types)
            _subscribers.append(_subscriber)
            _subscriptions.append(_subscriber.subscribe())

        _ticker.enable()
        _loop = asyncio.get_event_loop()

        _log.info(Fore.BLUE + 'starting IFS loop...')
        while _ifs.enabled:
            time.sleep(1.0)

        _loop.run_until_complete(asyncio.gather(_publish, *_subscriptions))

        _log.info(Fore.BLUE + 'closing {} subscribers...'.format(len(_subscribers)))
        for subscriber in _subscribers:
            _log.info(Fore.BLUE + 'subscriber {} processed {:d} messages, with {:d} remaining in queue: {}'.format(\
                    subscriber.name, subscriber.processed, subscriber.queue_length, _subscriber.print_queue_contents()))

        _ifs.disable()
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
