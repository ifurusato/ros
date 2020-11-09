#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# Copyright 2020 by Murray Altheim. All rights reserved. This file is part of
# the Robot OS project and is released under the "Apache Licence, Version 2.0".
# Please see the LICENSE file included as part of this package.
#
# author:   Murray Altheim
# created:  2020-04-27
# modified: 2020-05-21
#
#  A general purpose slew limiter that limits the rate of change of a value.
#

import time
from enum import Enum
from collections import deque
from colorama import init, Fore, Style
init()

try:
    import numpy
except ImportError:
    exit("This script requires the numpy module\nInstall with: sudo pip install numpy")

from lib.logger import Level, Logger
from lib.enums import Orientation


# ..............................................................................
class SlewRate(Enum): #       tested to 50.0 velocity:
    EXTREMELY_SLOW   = ( 0.3, 0.0034, 0.16, 0.0025 ) # 5.1 sec
    VERY_SLOW        = ( 1,   0.01,   0.22, 0.0002 ) # 3.1 sec
    SLOWER           = ( 2.5, 0.03,   0.38, 0.0005 ) # 1.7 sec
    SLOW             = ( 2,   0.05,   0.48, 0.0025 ) # 1.3 sec
    NORMAL           = ( 3,   0.08,   0.58, 0.0100 ) # 1.0 sec
    FAST             = ( 4,   0.20,   0.68, 0.0300) # 0.6 sec
    VERY_FAST        = ( 5,   0.4,    0.90, 0.0025 ) # 0.5 sec

    def __new__(cls, *args, **kwds):
        obj = object.__new__(cls)
        obj._value_ = args[0]
        return obj

    # ignore the first param since it's already set by __new__
    def __init__(self, num, ratio, pid, limit):
        self._ratio = ratio
        self._pid   = pid
        self._limit = limit

    # this makes sure the ratio is read-only
    @property
    def ratio(self):
        return self._ratio

    # this makes sure the ratio is read-only
    @property
    def pid(self):
        return self._pid

    # this makes sure the ratio is read-only
    @property
    def limit(self):
        return self._limit


# ..............................................................................
class SlewLimiter():
    '''
        A general purpose slew limiter that limits the rate of change of a value.

        This uses the ros:slew: section of the YAML configuration.

        Parameters:
            config: application configuration
            orientation: motor orientation, used only for logging label (optional)
            level: the logging Level
    '''
    def __init__(self, config, orientation, level):
        if orientation is None:
            self._log = Logger('slew', level)
        else:
            self._log = Logger('slew:{}'.format(orientation.label), level)
        self._millis  = lambda: int(round(time.time() * 1000))
        self._seconds = lambda: int(round(time.time()))
        self._clamp   = lambda n: self._minimum_output if n <= self._minimum_output else self._maximum_output if n >= self._maximum_output else n
        # Slew configuration .........................................
        cfg = config['ros'].get('slew')
        self._minimum_output    = cfg.get('minimum_output')
        self._maximum_output    = cfg.get('maximum_output')
        self._log.info('minimum output: {:5.2f}; maximum output: {:5.2f}'.format(self._minimum_output, self._maximum_output))
        self._rate_limit        = SlewRate.NORMAL.limit # default rate_limit: 0.0025 # value change permitted per millisecond
        self._stats_queue       = None
        self._start_time        = None
        self._enabled           = False
        self._filewriter        = None   # optional: for statistics
        self._filewriter_closed = False
        self._stats_start_time  = None   # used only for gnuplot stats
        self._log.info('ready.')

    # ..........................................................................
    def set_rate_limit(self, slew_rate):
        '''
            Sets the slew rate limit to the argument, in value/second. This
            overrides the value set in configuration. The default is NORMAL.
        '''
        if not isinstance(slew_rate, SlewRate):
            raise Exception('expected SlewRate argument, not {}'.format(type(slew_rate)))
        self._rate_limit = slew_rate.limit
        self._log.info('slew rate limit set to {:>6.4f}/cycle.'.format(self._rate_limit))

    # ..........................................................................
    def is_enabled(self):
        return self._enabled

    # ..........................................................................
    def enable(self):
        self._log.info('starting slew limiter with rate limit of {:5.3f}/cycle.'.format(self._rate_limit))
        self._enabled = True
        self._start_time = self._millis()
        self._stats_start_time = self._start_time
        self._log.info('enabled.')

#   # ..........................................................................
#   def start(self):
#       '''
#           Call start() to start the timer.

#           Note that this does not enable a slewed output; you must also
#           enable the limiter.
#       '''
#       self._log.info('starting slew limiter with rate limit of {:5.3f}/cycle.'.format(self._rate_limit))
#       self._enabled = True
#       self._start_time = self._millis()
#       self._stats_start_time = self._start_time

    # ..........................................................................
    def disable(self):
        self._log.info(Fore.MAGENTA + 'slew disabled.')
        self._enabled = False

    # ..........................................................................
    def reset(self, value):
        '''
            Resets the elapsed timer.
        '''
        self._start_time = self._millis()
        self._stats_start_time = self._start_time

    # ..........................................................................
    def slew(self, current_value, target_value):
        '''
            The returned result is the maximum amount of change between the current value
            and the target value based on the amount of elapsed time between calls (in
            milliseconds) multiplied by a constant set in configuration.

            If not enabled this returns the passed target value argument.
        '''
        if not self._enabled:
            self._log.warning('disabled; returning original target value {:+06.2f}.'.format(target_value))
            return target_value
        self._log.debug(Fore.BLACK + 'slew from current {:+06.2f} to target value {:+06.2f}.'.format(current_value, target_value))
        _now = self._millis()
        _elapsed = _now - self._start_time
        if target_value == current_value:
            _value = current_value
#           self._log.debug(Fore.BLACK + 'already there; returning target: {:+06.2f})'.format(_value))
        elif target_value > current_value: # increasing ..........
            _min = current_value - ( self._rate_limit * _elapsed )
            _max = current_value + ( self._rate_limit * _elapsed )
            _value = numpy.clip(target_value, _min, _max)
#           self._log.debug(Fore.GREEN + '-value: {:+06.2f} = numpy.clip(target_value: {:+06.2f}), _min: {:+06.2f}), _max: {:+06.2f}); elapsed: {:+06.2f}'.format(_value, target_value, _min, _max, _elapsed))
        else: # decreasing .......................................
            _min = current_value - ( self._rate_limit * _elapsed )
            _max = current_value + ( self._rate_limit * _elapsed )
            _value = numpy.clip(target_value, _min, _max)
#           self._log.debug(Fore.RED + '-value: {:+06.2f} = numpy.clip(target_value: {:+06.2f}), _min: {:+06.2f}), _max: {:+06.2f}); elapsed: {:+06.2f}'.format(_value, target_value, _min, _max, _elapsed))

        if self._filewriter: # write stats
            _stats_elapsed = _now - self._stats_start_time
            _data = '{:>5.3f}\t{:+06.2f}\t{:+06.2f}\n'.format(_stats_elapsed, _value, target_value)
            self._stats_queue.append(_data)

        # clip the output between min and max set in config (if negative we fix it before and after)
        if _value < 0:
            _clamped_value = -1.0 * self._clamp(-1.0 * _value)
        else:
            _clamped_value = self._clamp(_value)
#       self._log.debug('slew from current {:>6.2f} to target {:>6.2f} returns:'.format(current_value, target_value) \
#               + Fore.MAGENTA + '\t{:>6.2f}'.format(_clamped_value) + Fore.BLACK + ' (clamped from {:>6.2f})'.format(_value))
        return _clamped_value

   # ..............................................................................
    def set_filewriter(self, filewriter):
        '''
            If a FileWriter is set then the SlewLimiter will generate data
            and write this to a data file whose directory and filename are
            determined by configuration.
        '''
        self._filewriter = filewriter
        if self._filewriter:
            if self._stats_queue is None:
                self._stats_queue = deque()
            self._filewriter.enable(self._stats_queue)
            self._log.info('filewriter enabled.')

   # ..........................................................................
    def close_filewriter(self):
        if not self._filewriter_closed:
            self._filewriter_closed = True
            if self._filewriter:
                _tuning = [ '{:>4.2f}'.format(self._rate_limit) ] # this is actually a dummy
                self._filewriter.write_gnuplot_settings(_tuning)
                self._filewriter.disable()
            self._filewriter = None

#EOF
