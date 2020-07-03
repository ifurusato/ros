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

import time
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
class SlewLimiter():
    '''
        A general purpose slew limiter that limits the rate of change of a value.

        This uses the ros:slew: section of the YAML configuration.

        Parameters:
            config: application configuration
            orientation: motor orientation, used only for logging label
            level: the logging Level
    '''
    def __init__(self, config, orientation, level):
        self._log = Logger('slew:{}'.format(orientation.label), level)
        self._millis  = lambda: int(round(time.time() * 1000))
        self._seconds = lambda: int(round(time.time()))
        self._clamp = lambda n: self._minimum_output if n <= self._minimum_output else self._maximum_output if n >= self._maximum_output else n
        # Slew configuration .........................................
        cfg = config['ros'].get('slew')
        self._rate_limit = cfg.get('rate_limit')
        self._minimum_output = cfg.get('minimum_output')
        self._maximum_output = cfg.get('maximum_output')
        self._log.info('minimum output: {:5.2f}; maximum output: {:5.2f}'.format(self._minimum_output, self._maximum_output))
        self._stats_queue = None
        self._start_time = None
        self._enabled = False
        self._filewriter = None              # optional: for statistics
        self._filewriter_closed = False
        self._stats_start_time = None        # used only for gnuplot stats
        self._log.info('ready.')


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


    # ..........................................................................
    def set_rate_limit(self, rate_limit):
        '''
            Sets the slew rate limit to the argument, in value/second. This
            overrides the value set in configuration.
        '''
        self._rate_limit = rate_limit
        self._log.info('slew rate set to {:>4.2f}/sec.'.format(self._rate_limit))


    # ..........................................................................
    def start(self):
        '''
            Call start() to start the timer.

            Note that this does not enable a slewed output; you must also
            enable the limiter.
        '''
        self._log.info('starting slew limiter with rate limit of {:5.3f}/sec.'.format(self._rate_limit))
        self._enabled = True
        self._start_time = self._millis()
        self._stats_start_time = self._start_time


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
            The returned result is the maximum amount of change between the
            current value and the target value based on the amount of elapsed
            time between calls (in milliseconds) multiplied by a constant set
            in configuration.

            If not enabled this returns the passed target value argument.
        '''
        if not self._enabled:
            self._log.warning('disabled; returning original target value {:+06.2f}.'.format(target_value))
            return target_value
        self._log.debug('slew from current {:+06.2f} to target value {:+06.2f}.'.format(current_value, target_value))
        _now = self._millis()
        if target_value == current_value:   # increasing in value
            _value = current_value
            self._log.debug('already there; returning target: {:+06.2f})'.format(_value))
        else:
            _elapsed = _now - self._start_time
            _min = current_value - ( self._rate_limit * _elapsed )
            _max = current_value + ( self._rate_limit * _elapsed )
            _value = numpy.clip(target_value, _min, _max)
            self._log.debug('-value: {:+06.2f} = numpy.clip(target_value: {:+06.2f}), _min: {:+06.2f}), _max: {:+06.2f}); elapsed: {:+06.2f}'.format(_value, target_value, _min, _max, _elapsed))

        if self._filewriter: # write stats
            _stats_elapsed = _now - self._stats_start_time
            _data = '{:>5.3f}\t{:+06.2f}\t{:+06.2f}\n'.format(_stats_elapsed, _value, target_value)
            self._stats_queue.append(_data)

        # clip the output between min and max set in config
        _value = self._clamp(_value)
        self._log.info('slew from current {:+06.2f} to target {:+06.2f} returns:'.format(current_value, target_value) + Fore.MAGENTA + '\t{:+06.2f}'.format(_value) + Fore.CYAN + Style.NORMAL )
        return _value


    # ..........................................................................
    def is_enabled(self):
        return self._enabled


    # ..........................................................................
    def enable(self):
        self._log.info('enabled.')
        self._enabled = True


    # ..........................................................................
    def disable(self):
        self._log.info('disabled.')
        self._enabled = False


#EOF
