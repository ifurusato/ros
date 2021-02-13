#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# Copyright 2020 by Murray Altheim. All rights reserved. This file is part of
# the Robot OS project and is released under the "Apache Licence, Version 2.0".
# Please see the LICENSE file included as part of this package.
#
# author:  Murray Altheim
# created: 2020-03-16

import pytest
import time, sys, signal, traceback
from colorama import init, Fore, Style
init()

from lib.devnull import DevNull
from lib.logger import Logger, Level
from lib.config_loader import ConfigLoader
from lib.message_bus import MessageBus
from lib.message_factory import MessageFactory
from lib.queue import MessageQueue
from lib.battery import BatteryCheck
from lib.clock import Clock

INDEFINITE = True

# exception handler ............................................................
def signal_handler(signal, frame):
    print(Fore.RED + 'Ctrl-C caught: exiting...' + Style.RESET_ALL)
    sys.stderr = DevNull()
    print(Fore.CYAN + 'exit.' + Style.RESET_ALL)
    sys.exit(0)

# ..............................................................................
class MockConsumer():
    def __init__(self):
        self._log = Logger("consumer", Level.INFO)
        self._log.info('ready.')
        self._count = 0

    def add(self, message):
        if message:
            self._log.info(Fore.MAGENTA + 'event type: {}; message: {}'.format(message.event, message.value))
            self._count += 1
        else:
            self._log.warning('null message')

    @property
    def count(self):
        return self._count

# ..............................................................................
@pytest.mark.unit
def test_battery_check():

    _log = Logger("batcheck test", Level.INFO)
    _log.header('battery check', 'Starting test...', '[1/3]')
    _log.info(Fore.RED + 'Press Ctrl+C to exit.')

    # read YAML configuration
    _loader = ConfigLoader(Level.INFO)
    filename = 'config.yaml'
    _config = _loader.configure(filename)

    _log.header('battery check', 'Creating objects...', '[2/3]')

    _log.info('creating message factory...')
    _message_factory = MessageFactory(Level.INFO)
    _log.info('creating message queue...')
    _queue = MessageQueue(_message_factory, Level.INFO)
    _consumer = MockConsumer()
    _queue.add_consumer(_consumer)

    _log.info('creating message bus...')
    _message_bus = MessageBus(Level.INFO)

    _log.info('creating clock...')
    _clock = Clock(_config, _message_bus, _message_factory, Level.INFO)

    _log.info('creating battery check...')
    _battery_check = BatteryCheck(_config, _clock, _queue, _message_factory, Level.INFO)
    _battery_check.enable()
#   _battery_check.set_enable_messaging(True)
    _log.header('battery check', 'Enabling battery check...', '[3/3]')

    _clock.enable()

    while _battery_check.count < 40:
        time.sleep(0.5)

    _battery_check.close()
    _log.info('consumer received {:d} messages.'.format(_consumer.count))
    _log.info('complete.')

    # we don't expect any error messages to come through
    assert _consumer.count == 0


# ..............................................................................
def main():

    signal.signal(signal.SIGINT, signal_handler)
    try:
        test_battery_check()
    except KeyboardInterrupt:
        print(Fore.RED + 'Ctrl-C caught: complete.')
    except Exception as e:
        print(Fore.RED + 'error closing: {}\n{}'.format(e, traceback.format_exc()))

if __name__== "__main__":
    main()

#EOF
