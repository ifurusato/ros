#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# Copyright 2020 by Murray Altheim. All rights reserved. This file is part of
# the Robot OS project and is released under the "Apache Licence, Version 2.0".
# Please see the LICENSE file included as part of this package.
#
# author:   Murray Altheim
# created:  2020-04-27
# modified: 2020-04-27
#

import time
from colorama import init, Fore, Style
init()

try:
    import numpy
except ImportError:
    exit("This script requires the numpy module\nInstall with: sudo pip install numpy")

from lib.logger import Level, Logger
from lib.enums import Orientation, SlewRate, Speed
from lib.enums import Direction, Orientation


# ..............................................................................
class SlewLimiter():
    '''
        A general purpose slew limiter that limits the rate of change of a value.

        This uses the ros:slew: section of the YAML configuration.
    '''
    def __init__(self, config, orientation, level):
        self._log = Logger('slew:{}'.format(orientation.label), level)
        self._millis = lambda: int(round(time.time() * 1000))
        self._seconds = lambda: int(round(time.time()))
        # Slew configuration .........................................
        cfg = config['ros'].get('slewlimiter')
        _rate_limit = cfg.get('rate_limit')
        self.set_rate_limit(_rate_limit)
        self._previous_value = 0.0
        self._last_elapsed_sec = 0.0
        self._start_time = None
        self._enabled = False
        self._log.info('ready.')


    # ..........................................................................
    def set_rate_limit(self, rate_limit):
        '''
            Sets the slew rate limit to the argument, in value/second.
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


    # ..........................................................................
    def reset(self, value):
        '''
            Resets the elapsed timer and sets the previous value to the argument.
        '''
        self._previous_value = value
        self._log.info(Fore.RED + Style.BRIGHT + 'RESET to {:>5.2f}.'.format(self._previous_value))
        self._start_time = self._millis()
        self._last_elapsed_sec = 0.0

    # ..........................................................................
    def slew(self, direction, target_value):
        '''
            The returned result is the maximum amount of change between the
            current value and the target value.

            If not enabled this returns the passed argument.
        '''
        print('')
        self._log.info(Fore.BLUE + Style.BRIGHT + 'call slew()' + Fore.CYAN + Style.NORMAL + ' with target value {:+06.2f}; previous: {:+5.2f}.'.format(target_value, self._previous_value))
        if not self._enabled:
            self._log.warning('disabled; returning original target value {:+06.2f}.'.format(target_value))
            return target_value

#       if direction is Direction.FORWARD: pass else: pass
        _elapsed = self._millis() - self._start_time
        _diff_elapsed = self._last_elapsed_sec - _elapsed
        if target_value >= self._previous_value:   # increasing in value
            _min = -1.0 * self._rate_limit * _elapsed
            _max = self._rate_limit * _elapsed
            _value = numpy.clip(target_value, _min, _max)
            _diff = _value - self._previous_value
            self._log.info(Fore.MAGENTA + '_value: {:+06.2f}) = numpy.clip(target_value: {:+06.2f}), _min: {:+06.2f}), _max: {:+06.2f})\t    _diff: {:+06.2f}'.format(_value, target_value, _min, _max, _diff))
#           self._log.info(Fore.GREEN + '(min: {:+06.2f}) < (value: {:+06.2f}) < (max: {:+06.2f}); diff: {:+06.2f}'.format(_min, _value, _max, _diff))
        else:                                      # decreasing in value
            if _elapsed < 1.0:
                _elapsed = 1.0
#           _min = self._previous_value - (self._rate_limit * _elapsed)
#           _max = self._previous_value + (self._rate_limit * _elapsed)
            _min = -1.0 * self._rate_limit * _elapsed
            _max = self._rate_limit * _elapsed
            _value = numpy.clip(target_value, _min, _max)
            _diff = _value - self._previous_value
            self._log.info(Fore.YELLOW + '_value: {:+06.2f}) = numpy.clip(target_value: {:+06.2f}), _min: {:+06.2f}), _max: {:+06.2f})\t    _diff: {:+06.2f}'.format(_value, target_value, _min, _max, _diff))
#           self._log.info(Fore.RED   + '(min: {:+06.2f}) < (value: {:+06.2f}) < (max: {:+06.2f}); diff: {:+06.2f}'.format(_min, _value, _max, _diff))

        self._log.info(Fore.MAGENTA + Style.BRIGHT + 'returning value: {:+06.2f}'.format(_value)\
                + Fore.CYAN + Style.NORMAL + '\ttarget value: {:>5.2f}; previous: {:>5.2f};'.format(target_value, self._previous_value)\
                + Fore.BLACK + '\t {:>5.2f}ms elapsed (Δ {:>5.2f}ms); {:>5.2f} < {:>5.2f} < {:>5.2f}'.format(_elapsed, _diff_elapsed, _min, _diff, _max))

        self._previous_value = _value
        self._last_elapsed_sec = _elapsed
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
