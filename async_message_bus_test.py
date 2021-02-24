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
import uuid
import random
from colorama import init, Fore, Style
init()

from lib.event import Event
from lib.message import Message
from lib.message_factory import MessageFactory
from lib.logger import Logger, Level

#from mock.ifs import MockIntegratedFrontSensor

class MessageBus():

    def __init__(self, level=Level.DEBUG):
        self._log = Logger('bus', level)
        self._log.info('initialised MessageBus...')
        self._log.debug('MessageBus.__init__')
        self._message_factory = MessageFactory(Level.INFO)
        self._subscriptions = set()

    @property
    def subscriptions(self):
        return self._subscriptions

    def get_message_of_type(self, event, value):
        return self._message_factory.get_message(event, value)

    def publish(self, message: Message):
        self._log.info(Style.BRIGHT + 'publish message: {}'.format(message))
        for queue in self._subscriptions:
            queue.put_nowait(message)


# ..............................................................................
class Subscription():

    def __init__(self, message_bus, level=Level.DEBUG):
        self._log = Logger('subscription', level)
        self._log.info('__init__')
        self._message_bus = message_bus
        self.queue = asyncio.Queue()

    def __enter__(self):
        self._log.info('__enter__')
        self._message_bus._subscriptions.add(self.queue)
        return self.queue

    def __exit__(self, type, value, traceback):
        self._log.info('__exit__')
        self._message_bus._subscriptions.remove(self.queue)


# ..............................................................................
class Subscriber(object):

    def __init__(self, name, message_bus, level=Level.DEBUG):
        self._log = Logger('subscriber-{}'.format(name), level)
        self._name = name
        self._log.info(Fore.WHITE + 'Subscriber created.')
        self._message_bus = message_bus
        self._log.info('ready.')

    # ..............................................................................
    def receive_message(self, message):
        self._log.debug('Subscriber.receive_message(): {} rxd msg #{}: priority: {}; desc: "{}"; value: '.format(\
                self._name, message.number, message.priority, message.description) + Fore.YELLOW + Style.NORMAL + '{}'.format(message.value))

    # ..............................................................................
    async def subscribe(self):
        self._log.info(Style.DIM + 'subscribe called.')
        await asyncio.sleep(random.random() * 8)
        self._log.info(Fore.GREEN + 'Subscriber {} has subscribed.'.format(self._name))
    
        _message_count = 0
        # initial non-null message
        _message = self._message_bus.get_message_of_type(Event.NO_ACTION, 'noop')
        with Subscription(self._message_bus) as queue:
            while _message.event != Event.SHUTDOWN:
                _message = await queue.get()
                self.receive_message(_message)
                _message_count += 1
                self._log.info(Style.DIM + 'Subscriber {} rxd msg #{}: priority: {}; desc: "{}"; value: '.format(\
                        self._name, _message.number, _message.priority, _message.description) + Fore.YELLOW + Style.NORMAL + '{}'.format(_message.value))
                if random.random() < 0.1:
                    self._log.info(Fore.RED + 'Subscriber {} has received enough'.format(self._name))
                    break
    
        self._log.info(Fore.RED + 'Subscriber {} is shutting down after receiving {:d} messages.'.format(self._name, _message_count))


# ..............................................................................
class Publisher(object):

    def __init__(self, message_bus, level=Level.DEBUG):
        self._log = Logger('pub', level)
        self._log.info(Fore.WHITE + 'Publisher: create. .......... ')
        self._counter = itertools.count()
        self._message_bus = message_bus
        self._log.info('ready.')

    # ..........................................................................
    async def publish(self, iterations):
        self._log.info(Fore.MAGENTA + Style.BRIGHT + 'Publish called. ================================ ')
        for x in range(iterations):
            self._log.info(Fore.YELLOW + 'Publisher: I have {} subscribers now'.format(len(self._message_bus.subscriptions)))
            _uuid = str(uuid.uuid4())
            _message = self._message_bus.get_message_of_type(Event.EVENT_R1, 'msg_{:d}-{}'.format(x, _uuid))
            _message.number = next(self._counter)
            self._message_bus.publish(_message)
            await asyncio.sleep(1)
    
        _shutdown_message = self._message_bus.get_message_of_type(Event.SHUTDOWN, 'shutdown')
        self._message_bus.publish(_shutdown_message)

# ..............................................................................
class MySubscriber(Subscriber):
    def __init__(self, name, message_bus, level=Level.DEBUG):
        super().__init__(name, message_bus, level)
        self._log.info(Fore.BLUE + 'MySubscriber: create. ========  =============== ========= =========== ')
        self._log.info('ready.')

    # ..............................................................................
    def receive_message(self, message):
        time.sleep(3.0)
        self._log.info('MySubscriber.receive_message(): {} rxd msg #{}: priority: {}; desc: "{}"; value: '.format(\
                self._name, message.number, message.priority, message.description) + Fore.YELLOW + Style.NORMAL + '{}'.format(message.value))
        time.sleep(3.0)

    # ..............................................................................
    def subscribe(self):
        self._log.info(Fore.BLUE + 'MySubscriber.subscribe() called.  ================================== ')
        return super().subscribe()

# ..............................................................................
class MyPublisher(Publisher):
    def __init__(self, message_bus, level=Level.DEBUG):
        super().__init__(message_bus, level)
#       self._log = Logger('my-pub', level)
        self._log.info(Fore.YELLOW + 'MyPublisher: create. .......... ')
        self._log.info('ready.')

    # ..........................................................................
    def publish(self, iterations):
        self._log.info(Fore.MAGENTA + 'MyPublish called, passing... ========= ======= ======== ======= ======== ')
        return super().publish(iterations)

# main .........................................................................
#_log = Logger('main', Level.INFO)

def main(argv):

    _log = Logger("main", Level.INFO)
    try:

        _log.heading('configuration', 'configuring objects...', '[1/4]')
        _message_bus = MessageBus()
#       _publisher = Publisher(_message_bus)
        _publisher = MyPublisher(_message_bus)
        _publish = _publisher.publish(10)
#       _publisher = MockIntegratedFrontSensor(_message_bus)
#       _publisher.enable()
        _log.heading('subscriptions', 'generating subscribers...', '[2/4]')

        _subscriptions = []
        for x in range(10):
            _subscriber = MySubscriber('s{}'.format(x), _message_bus)
            _subscriptions.append(_subscriber.subscribe())

        loop = asyncio.get_event_loop()
        _log.heading('looping', 'starting loop...', '[3/4]')

        loop.run_until_complete(asyncio.gather(_publish, *_subscriptions))
        _log.heading('complete', 'loop complete.', '[4/4]')

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
