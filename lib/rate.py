#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# Copyright 2020 by Murray Altheim. All rights reserved. This file is part of
# the Robot Operating System project and is released under the "Apache Licence, 
# Version 2.0". Please see the LICENSE file included as part of this package.
#
# author:   Murray Altheim
# created:  2020-08-23
# modified: 2020-08-31
#
# derived from:  https://pypi.org/project/nxp-imu

import time
from colorama import init, Fore, Style
init()

from lib.logger import Level, Logger

# ..............................................................................
class Rate():

    def __init__(self, hertz, level=Level.INFO):
        self._log = Logger('rate', level)
        self._last_time = time.time()
        self._dt = 1/hertz
        self._log.info('rate set for {:d}Hz (period: {:>4.2f}sec/{:d}ms)'.format(hertz, self.get_period_sec(), self.get_period_ms()))

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
        _diff = time.time() - self._last_time
        if self._dt > _diff:
            time.sleep(self._dt - _diff)
        _elapsed = 1000 * (time.time() - self._last_time)
        self._last_time = time.time()
#       self._log.info(Fore.BLACK + Style.BRIGHT + 'elapsed: {:>6.3f}ms'.format(_elapsed))

#EOF
