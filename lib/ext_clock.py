#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# Copyright 2020 by Murray Altheim. All rights reserved. This file is part of
# the Robot OS project and is released under the "Apache Licence, Version 2.0".
# Please see the LICENSE file included as part of this package.
#
# author:   Murray Altheim
# created:  2021-02-19
# modified: 2021-02-19
#
# Uses an interrupt (event detect) set on a GPIO pin as an external Clock trigger.
#

import sys, itertools
from datetime import datetime as dt
from collections import deque as Deque
import RPi.GPIO as GPIO
from colorama import init, Fore, Style
init()

from lib.logger import Logger, Level

# ..............................................................................
class ExternalClock(object):

    def __init__(self, config, message_bus, level):
        if config is None:
            raise ValueError('no configuration provided.')
        self._message_bus = message_bus
        self._log = Logger("ext-clock", level)
        _clock_config = config['ros'].get('clock')
        self._loop_freq_hz = _clock_config.get('loop_freq_hz')
        self._log.info('tick frequency: {:d}Hz'.format(self._loop_freq_hz))
        self._dt_s = 1 / self._loop_freq_hz
        self._log.info('frequency: {}s'.format( self._dt_s ))
        self._dt_ms = 50.0 # loop delay in milliseconds 
        self._log.info('frequency: {}ms'.format( self._dt_ms ))
        _config = config['ros'].get('external_clock')
        self._pin = _config.get('pin')
        self._log.info('external clock input pin: {}'.format( self._pin ))
        GPIO.setmode(GPIO.BCM)
        GPIO.setup(self._pin, GPIO.IN, pull_up_down=GPIO.PUD_UP)
        self._enabled = False
        _queue_limit = 50 # larger number means it takes longer to change
        self._queue  = Deque([], maxlen=_queue_limit)
        self._counter = itertools.count()
        self._last_time = dt.now()
        self._log.info('ready.')

    # ..........................................................................
    def enable(self):
        if self._enabled:
            self._log.info('already enabled.')
        else:
            self._enabled = True
            GPIO.add_event_detect(self._pin, GPIO.BOTH, 
                    callback=self._tick_callback,
                    bouncetime=10) # ms, shouldn't be much need

    # ..........................................................................
    def _get_mean(self, value):
        '''
        Returns the mean of measured values.
        '''
        self._queue.append(value)
        _n = 0
        _mean = 0.0
        for x in self._queue:
            _n += 1
            _mean += ( x - _mean ) / _n
        if _n < 1:
            return float('nan');
        else:
            return _mean

    # ..........................................................................
    def disable(self):
        if self._enabled:
            GPIO.remove_event_detect(self._pin)
        else:
            self._log.info('already disabled.')

    # ..........................................................................
    def _tick_callback(self, value):
        if self._enabled:
            self._count = next(self._counter)
            if self._count > 1000: 
                self._log.info('reached count limit, exiting...')
                sys.exit(0)
            _now = dt.now()
            _delta_ms = 1000.0 * (_now - self._last_time).total_seconds()
            _error_ms = _delta_ms - self._dt_ms

            _mean = self._get_mean(_delta_ms)

            if _error_ms > 0.5000:
                self._log.info(Fore.RED + Style.BRIGHT + '[{:05d}]\tdelta {:8.5f}ms; error: {:8.5f}ms; '.format(self._count, _delta_ms, _error_ms) 
                        + Fore.MAGENTA + '; mean: {:8.5f}'.format(_mean))
            elif _error_ms > 0.1000:
                self._log.info(Fore.YELLOW + Style.BRIGHT + '[{:05d}]\tdelta {:8.5f}ms; error: {:8.5f}ms; '.format(self._count, _delta_ms, _error_ms)
                        + Fore.MAGENTA + '; mean: {:8.5f}'.format(_mean))
            else:
                self._log.info(Fore.GREEN  + '[{:05d}]\tdelta {:8.5f}ms; error: {:8.5f}ms; '.format(self._count, _delta_ms, _error_ms)
                        + Fore.MAGENTA + '; mean: {:8.5f}'.format(_mean))
            self._last_time = _now

#EOF
