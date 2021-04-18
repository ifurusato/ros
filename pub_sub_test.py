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
import sys, traceback
from colorama import init, Fore, Style
init()

from lib.config_loader import ConfigLoader
from lib.logger import Logger, Level
from lib.async_message_bus import MessageBus
from lib.message_factory import MessageFactory
from lib.publisher import Publisher
from lib.subscriber import Subscriber
from lib.ticker import Ticker
from lib.event import Event

from mock.publisher import IfsPublisher

#from mock.motor_configurer import MotorConfigurer
#from mock.motors import Motors

# main .........................................................................
def main():

    _log = Logger("main", Level.INFO)
    _log.info(Fore.BLUE + 'configuring pub-sub test...')

    # read YAML configuration
    _loader = ConfigLoader(Level.INFO)
    filename = 'config.yaml'
    _config = _loader.configure(filename)

    _loop_freq_hz = 10
    _ticker = Ticker(_loop_freq_hz, Level.INFO)

    _message_bus = MessageBus(Level.DEBUG)
    _message_factory = MessageFactory(_message_bus, Level.INFO)

    _publisher1  = IfsPublisher('A', _message_bus, _message_factory)
#   _publisher1  = Publisher('A', _message_bus, _message_factory)
    _message_bus.register_publisher(_publisher1)
#   _publisher2  = Publisher('B', _message_bus, _message_factory, Level.INFO)
#   _message_bus.register_publisher(_publisher2)

    # ROAM is commonly accepted by all subscribers

#   _subscriber1 = Subscriber('behaviour', Fore.YELLOW, _message_bus, Level.INFO)
#   _subscriber1.events = [ Event.ROAM, Event.SNIFF ] # reacts to ROAM and SNIFF
#   _message_bus.register_subscriber(_subscriber1)

    _subscriber2 = Subscriber('infrared', Fore.MAGENTA, _message_bus, Level.INFO)
    _subscriber2.events = [ Event.INFRARED_PORT, Event.INFRARED_CNTR, Event.INFRARED_STBD ] # reacts to IR
    _subscriber2.add_event(Event.ROAM)
    _message_bus.register_subscriber(_subscriber2)

    _subscriber3 = Subscriber('bumper', Fore.GREEN, _message_bus, Level.INFO)
    _subscriber3.events = [ Event.SNIFF, Event.BUMPER_PORT, Event.BUMPER_CNTR, Event.BUMPER_STBD ] # reacts to bumpers
    _subscriber3.add_event(Event.ROAM)
    _message_bus.register_subscriber(_subscriber3)

    _motors = None
    # add motor controller, reacts to STOP, HALT, BRAKE, INCREASE_SPEED and DECREASE_SPEED
#   _motor_configurer = MotorConfigurer(_config, _ticker, _message_bus, enable_mock=True, level=Level.INFO)
#   _motors = _motor_configurer.get_motors() 
#   _motors.add_event(Event.ROAM)
#   _message_bus.register_subscriber(_motors)

    _message_bus.print_publishers()
    _message_bus.print_subscribers()

#   sys.exit(0)

    try:
        if _motors:
            _motors.enable()
        _message_bus.enable()
    except KeyboardInterrupt:
        _log.info('publish-subscribe interrupted')
    except Exception as e:
        _log.error('error in pub-sub: {} / {}'.format(e, traceback.print_stack()))
    finally:
        _message_bus.close()
        _log.info('successfully shutdown the message bus service.')

# ........................
if __name__ == "__main__":
    main()

