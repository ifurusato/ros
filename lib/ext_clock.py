#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# Copyright 2020-2021 by Murray Altheim. All rights reserved. This file is part
# of the Robot Operating System project, released under the MIT License. Please
# see the LICENSE file included as part of this package.
#
# author:   Murray Altheim
# created:  2021-02-19
# modified: 2021-02-19
#
# Uses an interrupt (event detect) set on a GPIO pin as an external Clock trigger.
#

import sys, itertools
from datetime import datetime as dt
import RPi.GPIO as GPIO
from collections import deque as Deque
import statistics
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
        # testing ....................
        self._queue_len = 50 # larger number means it takes longer to change
        self._queue  = Deque([], maxlen=self._queue_len)
        self._counter = itertools.count()
        self._last_time = dt.now()
        self._max_error = 0.0
        self._max_vari  = 0.0
        self._log.info('ready.')

    # ..........................................................................
    @property
    def enabled(self):
        return self._enabled

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
            _now = dt.now()
            self._count = next(self._counter)
            _delta_ms = 1000.0 * (_now - self._last_time).total_seconds()
            _mean = self._get_mean(_delta_ms)
            if len(self._queue) > 5:
                _error_ms = _delta_ms - self._dt_ms
                self._max_error = max(self._max_error, _error_ms)
                _vari1 = statistics.variance(self._queue) # if len(self._queue) > 5 else 0.0
                _vari  = sum((item - _mean)**2 for item in self._queue) / (len(self._queue) - 1)
                if self._count <= self._queue_len:
                    _vari = 0.0
                    self._max_vari = 0.0
                else:
                    self._max_vari = max(self._max_vari, _vari)
                if _error_ms > 0.5000:
                    self._log.info(Fore.RED + Style.BRIGHT + '[{:05d}]\tΔ {:8.5f}; err: {:8.5f}; '.format(self._count, _delta_ms, _error_ms) 
                            + Fore.CYAN + Style.NORMAL + 'max err: {:8.5f}; mean: {:8.5f}; max vari: {:8.5f}'.format(self._max_error, _mean, self._max_vari))
                elif _error_ms > 0.1000:
                    self._log.info(Fore.YELLOW + Style.BRIGHT + '[{:05d}]\tΔ {:8.5f}; err: {:8.5f}; '.format(self._count, _delta_ms, _error_ms)
                            + Fore.CYAN + Style.NORMAL + 'max err: {:8.5f}; mean: {:8.5f}; max vari: {:8.5f}'.format(self._max_error, _mean, self._max_vari))
                else:
                    self._log.info(Fore.GREEN  + '[{:05d}]\tΔ {:8.5f}; err: {:8.5f}; '.format(self._count, _delta_ms, _error_ms)
                            + Fore.CYAN                + 'max err: {:8.5f}; mean: {:8.5f}; max vari: {:8.5f}'.format(self._max_error, _mean, self._max_vari))
            else:
                self._log.info(Fore.CYAN + '[{:05d}]\tΔ {:8.5f}; '.format(self._count, _delta_ms) + Fore.CYAN + 'mean: {:8.5f}'.format(_mean))

            self._last_time = _now
            if self._count > 1000: 
                self._log.info('reached count limit, exiting...')
                self._enabled = False
#               sys.exit(0)

#EOF
