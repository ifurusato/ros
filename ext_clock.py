#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# Copyright 2020 by Murray Altheim. All rights reserved. This file is part of
# the Robot OS project and is released under the "Apache Licence, Version 2.0".
# Please see the LICENSE file included as part of this package.
#
# Uses an interrupt set on a GPIO pin as an external Clock trigger.
#

import sys, time
from datetime import datetime as dt
import RPi.GPIO as GPIO
from colorama import init, Fore, Style
init()

from lib.logger import Logger, Level
from lib.message_bus import MessageBus

# ..............................................................................
class ExternalClick(object):

    def __init__(self, pin, message_bus, level):
        self._log = Logger("xclock", level)
        self._pin = pin
        GPIO.setmode(GPIO.BCM)
        GPIO.setup(self._pin, GPIO.IN, pull_up_down=GPIO.PUD_UP)
        self._dt_ms = 50.0 # loop delay in milliseconds 
        self._last_time = dt.now()
#       _event_type = GPIO.RISING
#       _event_type = GPIO.FALLING
        self._event_type = GPIO.BOTH
        self._enabled = False
        self._log.info('ready.')

    def enable(self):
#       GPIO.wait_for_edge(_pin, self._event_type)
        if self._enabled:
            self._log.info('already enabled.')
        else:
            self._enabled = True
            GPIO.add_event_detect(self._pin, GPIO.BOTH, 
                    callback=self.clock_pulse_received,
                    bouncetime=10) # ms, shouldn't be much need

    def clock_pulse_received(self, value):
        _now = dt.now()
        _delta_ms = 1000.0 * (_now - self._last_time).total_seconds()
        _error_ms = _delta_ms - self._dt_ms
        if _error_ms > 0.5000:
            self._log.info(Fore.RED + Style.BRIGHT + 'delta {:8.5f}ms; error: {:8.5f}ms; '.format(_delta_ms, _error_ms))
        elif _error_ms > 0.1000:
            self._log.info(Fore.YELLOW + Style.BRIGHT + 'delta {:8.5f}ms; error: {:8.5f}ms; '.format(_delta_ms, _error_ms))
        else:
            self._log.info(Fore.GREEN  + 'delta {:8.5f}ms; error: {:8.5f}ms; '.format(_delta_ms, _error_ms))
        self._last_time = _now


# main .........................................................................

def main(argv):

    _log = Logger("xclock", Level.INFO)
    _log.info('starting test...')

    _pin = 5
    _message_bus = MessageBus(Level.INFO)
    _clock = ExternalClick(_pin, _message_bus, Level.INFO)

    try:

        _log.info('starting clock...')
        _clock.enable()

        while True:
            time.sleep(1.0)

    except KeyboardInterrupt:
        _log.info("caught Ctrl-C.")
    finally:
        _log.info("closed.")

# call main ....................................................................
if __name__== "__main__":
    main(sys.argv[1:])

#EOF
