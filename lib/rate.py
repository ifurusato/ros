#!/usr/bin/env python3.7
# -*- coding: utf-8 -*-
#
# Copyright 2020 by Murray Altheim. All rights reserved. This file is part of
# the Robot Operating System project and is released under the "Apache Licence, 
# Version 2.0". Please see the LICENSE file included as part of this package.
#
# author:   Murray Altheim
# created:  2020-08-23
# modified: 2020-10-27
#

import time
from colorama import init, Fore, Style
init()

from lib.logger import Level, Logger

# ..............................................................................
class Rate():
    '''
       Loops at a fixed rate, specified in hertz (Hz).

       :param hertz:   the frequency of the loop in Hertz
       :param level:   the log level
       :param use_ns:  (optional) if True use a nanosecond counter instead of milliseconds
    '''
    def __init__(self, hertz, level=Level.INFO, use_ns=False):
        self._log = Logger('rate', level)
        self._last_ns   = time.perf_counter_ns()
        self._last_time = time.time()
        self._dt = 1/hertz
        self._dt_ms = self._dt * 1000
        self._dt_ns = self._dt_ms * 1000000
        self._use_ns = use_ns
        if self._use_ns:
            self._log.info('nanosecond rate set for {:d}Hz (period: {:>4.2f}sec/{:d}ms)'.format(hertz, self.get_period_sec(), self.get_period_ms()))
        else:
            self._log.info('millisecond rate set for {:d}Hz (period: {:>4.2f}sec/{:d}ms)'.format(hertz, self.get_period_sec(), self.get_period_ms()))

    # ..........................................................................
    def get_period_sec(self):
        '''
            Returns the period in seconds, as a float.
        '''
        return self._dt

    # ..........................................................................
    def get_period_ms(self):
        '''
            Returns the period in milliseconds, rounded to an int.
        '''
        return round(self._dt * 1000)


    # ..........................................................................
    def waiting(self):
        '''
           Return True if still waiting for the current loop to complete.
        '''
        return self._dt < ( time.time() - self._last_time )

    # ..........................................................................
    def wait(self):
        """
            If called before the allotted period will wait the remaining time
            so that the loop is no faster than the specified frequency. If
            called after the allotted period has passed, no waiting takes place.

            E.g.:

                # execute loop at 60Hz
                rate = Rate(60)

                while True:
                    # do something...
                    rate.wait()

        """
        if self._use_ns:
            _ns_diff = time.perf_counter_ns() - self._last_ns
            _delay_sec = ( self._dt_ns - _ns_diff ) / ( 1000 * 1000000 )
            if self._dt_ns > _ns_diff:
#               print('...')
                time.sleep(_delay_sec)
#           self._log.info(Fore.BLACK + Style.BRIGHT + 'dt_ns: {:7.4f}; diff: {:7.4f}ns; delay: {:7.4f}s'.format(self._dt_ns, _ns_diff, _delay_sec))
            self._last_ns = time.perf_counter_ns()
        else:
            _diff = time.time() - self._last_time
            _delay_sec = self._dt - _diff
            if self._dt > _diff:
                time.sleep(_delay_sec)
#           self._log.info(Fore.BLACK + Style.BRIGHT + 'dt: {:7.4f}; diff: {:7.4f}ms; delay: {:7.4f}s'.format(self._dt, _diff, _delay_sec))
            self._last_time = time.time()

#       _elapsed = 1000 * (time.time() - self._last_time)
#       self._log.info(Fore.BLACK + Style.BRIGHT + 'elapsed: {:>6.3f}ms'.format(_elapsed))

#EOF



