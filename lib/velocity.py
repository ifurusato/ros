#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# Copyright 2020 by Murray Altheim. All rights reserved. This file is part of
# the Robot OS project and is released under the "Apache Licence, Version 2.0".
# Please see the LICENSE file included as part of this package.
#
# author:   Murray Altheim
# created:  2020-09-13
# modified: 2020-09-13
#
# Unlike other enums this one requires configuration as it involves the
# specifics of the motor encoders and physical geometry of the robot.
# Unconfigured it always returns 0.0, which is harmless but not useful.

import math
from enum import Enum
from colorama import init, Fore, Style
init()

from lib.logger import Level, Logger

# ..............................................................................
class Velocity(Enum):
    '''
        A Velocity Enum, which for each enumerated velocity provides an ability
        to set a specific number of encoder steps per second corresponding to a
        given velocity in cm/sec.

        Setting the velocity values is expected to be done via the Geometry
        class, which contains information such as wheel diameter.

        Notes ....................................

        Tasks: 
          1. measure unloaded wheel speed (in ticks per second, from encoders)
             to set maximum velocity as upper limit
          2. design a reasonable range from 0 to 100% and establish a set of 
             enumerated values that represent named velocities, e.g., "HALF"
          3. figure out how many ticks per second the upper limit represents
          4. figure out how many ticks per 20Hz (50ms) loop that represents
    '''

    STOP          = ( 0,  0.0,  0.0 )
    DEAD_SLOW     = ( 1, 10.0,  0.0 )
    SLOW          = ( 2, 25.0,  0.0 )
    ONE_THIRD     = ( 3, 33.3,  0.0 )
    HALF          = ( 4, 50.0,  0.0 )
    TWO_THIRDS    = ( 5, 66.6,  0.0 )
    THREE_QUARTER = ( 6, 75.0,  0.0 )
    FULL          = ( 7, 90.0,  0.0 )
    MAXIMUM       = ( 8, 100.0, 0.0 )

    # ignore the first param since it's already set by __new__
    def __init__(self, num, percent, value):
        self._log = Logger('velocity', Level.INFO)
        self._percent = percent
        self._value = value # how many ticks per 20Hz loop?

    # ..........................................................................
    @property
    def percentage(self):
        '''
            Returns the velocity as a percentage.
        '''
        return self._percent

    # ..........................................................................
    @property
    def value(self):
        '''
            Returns the number of ticks per second
        '''
        return self._value

    @value.setter
    def value(self, value):
        '''
            Sets the number of ticks per second for a given Velocity.
        '''
        self._value = value

    # ..........................................................................
    @staticmethod
    def get_slower_than(velocity):
        '''
            Provided a value between 0-100, return the next lower Velocity.
        '''
        if velocity < Velocity.DEAD_SLOW.value:
            return Velocity.STOP
        elif velocity < Velocity.SLOW.value:
            return Velocity.DEAD_SLOW
        elif velocity < Velocity.ONE_THIRD.value:
            return Velocity.SLOW
        elif velocity < Velocity.HALF.value:
            return Velocity.ONE_THIRD
        elif velocity < Velocity.TWO_THIRDS.value:
            return Velocity.HALF
        elif velocity < Velocity.THREE_QUARTER.value:
            return Velocity.TWO_THIRDS
        elif velocity < Velocity.FULL.value:
            return Velocity.THREE_QUARTER
        else:
            return Velocity.FULL

#EOF
