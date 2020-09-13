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
        Provides a configurable Velocity Enum, which returns encoder steps
        per second corresponding to a given velocity in cm/sec.

        To configure, call:

            Velocity.CONFIG.configure(_config)

        Notes ....................................

        Tasks: 
          1. measure unloaded wheel speed (in ticks per second, from encoders)
             to set maximum velocity as upper limit
          2. design a reasonable range from 0 to 100% and establish a set of 
             enumerated values that represent named velocities, e.g., "HALF"
          3. figure out how many ticks per second the upper limit represents
          4. figure out how many ticks per 20Hz (50ms) loop that represents

        494 encoder steps per rotation (maybe 493)
        68.5mm diameter tires
        215.19mm/21.2cm wheel circumference
        1 wheel rotation = 215.2mm
        2295 steps per meter
        2295 steps per second  = 1 m/sec
        2295 steps per second  = 100 cm/sec
        229.5 steps per second = 10 cm/sec
        22.95 steps per second = 1 cm/sec

        1 rotation = 215mm = 494 steps
        1 meter = 4.587 rotations
        2295.6 steps per meter
        22.95 steps per cm
    '''

    CONFIG        = ( 0,  0.0, -1.0 )
    STOP          = ( 1,  0.0,  0.0 )
    DEAD_SLOW     = ( 2, 10.0,  0.0 )
    SLOW          = ( 3, 25.0,  0.0 )
    ONE_THIRD     = ( 4, 33.3,  0.0 )
    HALF          = ( 5, 50.0,  0.0 )
    TWO_THIRDS    = ( 6, 66.6,  0.0 )
    THREE_QUARTER = ( 7, 75.0,  0.0 )
    FULL          = ( 8, 90.0,  0.0 )
    MAXIMUM       = ( 9, 100.0, 0.0 )

    # ignore the first param since it's already set by __new__
    def __init__(self, num, percent, value):
        self._log = Logger('velocity', Level.INFO)
        self._percent = percent
        self._value = value # how many ticks per 20Hz loop?

    # ..........................................................................
    def configure(self, config):
        if config is None:
            raise ValueError('null configuration argument.')
        _config = config['ros'].get('geometry')
        self._wheel_diameter    = _config.get('wheel_diameter')
        self._wheelbase         = _config.get('wheelbase')
        self._step_per_rotation = _config.get('steps_per_rotation')
        _wheel_circumference    = math.pi * self._wheel_diameter # mm
        self._steps_per_m       = 1000.0 * self._step_per_rotation  / _wheel_circumference 
        self._steps_per_cm      = 10.0 * self._step_per_rotation  / _wheel_circumference 
        self._log.info( Fore.BLUE + Style.BRIGHT + '{:5.2f} steps per m.'.format(self._steps_per_m))
        self._log.info( Fore.BLUE + Style.BRIGHT + '{:5.2f} steps per cm.'.format(self._steps_per_cm))
        # TODO set values for each enumeration

        self._log.info('ready.')

    # ..........................................................................
    @property
    def percentage(self):
        return self._percent

    # ..........................................................................
    @property
    def value(self):
        '''
            Returns the number of ticks per second
        '''
        return self._value

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

