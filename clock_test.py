#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# Copyright 2020-2021 by Murray Altheim. All rights reserved. This file is part
# of the Robot Operating System project, released under the MIT License. Please
# see the LICENSE file included as part of this package.
#
# author:   Murray Altheim
# created:  2020-10-27
# modified: 2020-10-27
#

import pytest
import time, itertools, traceback
from datetime import datetime as dt
from colorama import init, Fore, Style
init()

from lib.logger import Logger, Level
from lib.config_loader import ConfigLoader
from lib.event import Event
from lib.message_factory import MessageFactory
from lib.clock import Clock

INFINITE = True
SHOW_STATS = False

# ..............................................................................
class MockMessageBus():
    '''
    This message queue just displays filtered, clock-related events as they arrive.
    '''
    def __init__(self, level):
        super().__init__()
        self._counter = itertools.count()
        self._log = Logger("queue", Level.INFO)
        self._start_time = dt.now()
        self._last_time  = self._start_time
        self._log.info('ready.')

    # ......................................................
    def set_clock(self, clock):
        self._clock = clock

    # ......................................................
    def add(self, message):
        global tock_count
        message.number = next(self._counter)
        self._log.debug('added message {:06d}: priority {}: {}'.format(message.number, message.priority, message.description))
        _event = message.event
        _value = message.value

        _now = dt.now()
        _delta = _now - self._start_time
        _elapsed_ms = (_now - self._last_time).total_seconds() * 1000.0
        _process_delta = _now - message.timestamp
        _elapsed_loop_ms = _delta.total_seconds() * 1000.0
        _process_ms = _process_delta.total_seconds() * 1000.0
        _total_ms = _elapsed_loop_ms + _process_ms

        if SHOW_STATS:
            if _event is Event.CLOCK_TICK:
#               self._log.info(Fore.YELLOW + Style.NORMAL + 'CLOCK_TICK: {}; value: {}'.format(_event.description, _value))
                self._log.info(Fore.BLACK  + Style.DIM + 'event: {}; proc time: {:8.5f}ms; tick loop: {:5.2f}ms; total: {:5.2f}ms; '.format(\
                        _event.description, _process_ms, _elapsed_loop_ms, _total_ms) + Fore.WHITE + Style.NORMAL \
                        + ' elapsed: {:6.3f}ms; trim: {:7.4f}'.format(_elapsed_ms, self._clock.trim))
            elif _event is Event.CLOCK_TOCK:
                self._log.info(Fore.YELLOW + Style.DIM + 'event: {}; proc time: {:8.5f}ms; tock loop: {:5.2f}ms; total: {:6.3f}ms; '.format(\
                        _event.description, _process_ms, _elapsed_loop_ms, _total_ms) + Fore.WHITE + Style.NORMAL \
                        + ' elapsed: {:6.3f}ms; trim: {:7.4f}'.format(_elapsed_ms, self._clock.trim))
                self._start_time = _now
                tock_count += 1
            else:
                self._log.info(Fore.BLACK + Style.BRIGHT + 'other event: {}'.format(_event.description))

        self._last_time = _now

# ..............................................................................
@pytest.mark.unit
def test_clock():
    global tock_count
    _log = Logger('clock-test', Level.INFO)
    _loader = ConfigLoader(Level.INFO)
    filename = 'config.yaml'
    _config = _loader.configure(filename)

    tock_count = 0
    _message_factory = MessageFactory(Level.INFO)
    _message_bus = MockMessageBus(Level.INFO)
    _clock = Clock(_config, _message_bus, _message_factory, Level.INFO)
    _message_bus.set_clock(_clock)
    _clock.enable()
    _log.info('ready; begin test.')
    _loops = 3
    while INFINITE or tock_count < _loops:
        time.sleep(1.0)
    _log.info('test complete.')

# ..............................................................................
def main():

    try:
        test_clock()
    except KeyboardInterrupt:
        print(Fore.RED + 'Ctrl-C caught; exiting...' + Style.RESET_ALL)
    except Exception as e:
        print(Fore.RED + Style.BRIGHT + 'error starting ifs: {}\n{}'.format(e, traceback.format_exc()) + Style.RESET_ALL)
    finally:
        pass

if __name__== "__main__":
    main()

#EOF
