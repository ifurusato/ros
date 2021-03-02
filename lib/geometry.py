#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# Copyright 2020-2021 by Murray Altheim. All rights reserved. This file is part
# of the Robot Operating System project, released under the MIT License. Please
# see the LICENSE file included as part of this package.
#
# author:   Murray Altheim
# created:  2020-09-13
# modified: 2020-09-13
#
# Unlike other enums this one requires configuration as it involves the
# specifics of the motor encoders and physical geometry of the robot.
# Unconfigured it always returns 0.0, which is harmless but not useful.
#

import math
from enum import Enum
from colorama import init, Fore, Style
init()

from lib.logger import Level, Logger

# ..............................................................................
class Geometry(object):
    '''
        Provides a configurable Geometry class, which is used for step,
        distance (cm) and velocity (cm/sec) calculations.

        To configure, call:

            Geometry geo = Geometry(config)

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

    # ..........................................................................
    def __init__(self, config, level):
        if config is None:
            raise ValueError('null configuration argument.')
        _config = config['ros'].get('geometry')
        self._log = Logger("geo", level)
        self._wheel_diameter     = _config.get('wheel_diameter')
        self._wheelbase          = _config.get('wheelbase')
        self._steps_per_rotation = _config.get('steps_per_rotation')
        _wheel_circumference     = math.pi * self._wheel_diameter # mm
        self._steps_per_m        = 1000.0 * self._steps_per_rotation  / _wheel_circumference 
        self._steps_per_cm       = 10.0 * self._steps_per_rotation  / _wheel_circumference 
        self._log.info( Fore.BLUE + Style.BRIGHT + '{:5.2f} steps per m.'.format(self._steps_per_m))
        self._log.info( Fore.BLUE + Style.BRIGHT + '{:5.2f} steps per cm.'.format(self._steps_per_cm))
        # TODO set values for each enumeration
        self._log.info('ready.')

    # ..........................................................................
    @property
    def steps_per_rotation(self):
        return self._steps_per_rotation
    # ..........................................................................
    @property
    def steps_per_meter(self):
        return self._steps_per_m

    # ..........................................................................
    @property
    def steps_per_cm(self):
        return self._steps_per_cm

#EOF
