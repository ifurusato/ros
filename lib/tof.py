#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# Copyright 2020-2021 by Murray Altheim. All rights reserved. This file is part
# of the Robot Operating System project, released under the MIT License. Please
# see the LICENSE file included as part of this package.
#
# author:   altheim
# created:  2020-03-31
# modified: 2020-03-31
#

import sys
from enum import Enum

try:
    import VL53L1X
except ImportError:
    sys.exit("This script requires the vl53l1x module\nInstall with: pip3 install --user vl53l1x")

from lib.logger import Level, Logger

UPDATE_TIME_MICROS = 66000
INTER_MEASUREMENT_PERIOD_MILLIS = 70

#UPDATE_TIME_MICROS = 50000
#INTER_MEASUREMENT_PERIOD_MILLIS = 53

class Range(Enum):
    UNCHANGED   = 0 # = Unchanged
    SHORT       = 1 # Short Range
    MEDIUM      = 2 # Medium Range
    LONG        = 3 # Long Range
    PERFORMANCE = 4 # custom

    @staticmethod
    def from_str(label):
        if label.upper() == 'UNCHANGED':
            return Range.UNCHANGED
        elif label.upper() == 'SHORT':
            return Range.SHORT
        elif label.upper() == 'MEDIUM':
            return Range.MEDIUM
        elif label.upper() == 'LONG':
            return Range.LONG
        elif label.upper() == 'PERFORMANCE':
            return Range.PERFORMANCE
        else:
            raise NotImplementedError


class TimeOfFlight():
    '''
        This is based on Pimoroni's VL53L1X Time of Flight (ToF) Breakaway Garden board,
        which has a 4-400cm range (27° field of view), up to 50Hz ranging frequency, and
        an accuracy of +/-25mm (+/-20mm in the dark).

    '''
    def __init__(self, range_value, level):
        self._log = Logger("tof", level)
        self._range = range_value
#       self._tof = VL53L1X.VL53L1X(i2c_bus=1, i2c_address=0x29)
        self._tof = VL53L1X.VL53L1X()
        self._tof.open()
        # Optionally set an explicit timing budget. These values are measurement time
        # in microseconds, and inter-measurement time in milliseconds. If you uncomment
        # the line below to set a budget you should use `self._tof.start_ranging(0)`
        # self._tof.set_timing(66000, 70)

        # lower timing budgets allow for faster updates, but sacrifice accuracy
        if self._range is Range.PERFORMANCE:
            self._tof.set_timing(UPDATE_TIME_MICROS, INTER_MEASUREMENT_PERIOD_MILLIS)
        self._log.info('ready.')

    # ..........................................................................
    def read_distance(self):
        '''
        Return the range in mm. This function will block until a reading is returned.
        '''
        distance_in_mm = self._tof.get_distance()
        self._log.debug('distance: {:d}mm'.format(distance_in_mm))
        return distance_in_mm

    # ..........................................................................
    def enable(self):
        if self._range is Range.PERFORMANCE:
            self._tof.start_ranging(Range.UNCHANGED.value)
            self._log.info('enabled with high performance.')
        else:
            self._tof.start_ranging(self._range.value)
            self._log.info('enabled with {} range.'.format(self._range.name))

    # ..........................................................................
    def disable(self):
        self._tof.stop_ranging()
        self._log.info('disabled.')

#EOF
