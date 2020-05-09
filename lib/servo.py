#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# Copyright 2020 by Murray Altheim. All rights reserved. This file is part of
# the Robot OS project and is released under the "Apache Licence, Version 2.0".
# Please see the LICENSE file included as part of this package.
#
# author:   Murray Altheim
# created:  2020-03-31
# modified: 2020-03-31

import sys, time
sys.path.append('/home/pi/ultraborg')
from lib.UltraBorg3 import UltraBorg as UltraBorg
import lib.UltraBorg3

from lib.logger import Level, Logger

class Servo():
    '''
        This currently is hardcoded to use Servo 1.
    '''
    def __init__(self, level):
        self._log = Logger("servo", level)
        self._UB = UltraBorg()         # create a new UltraBorg object
        self._UB.Init()                # initialise the board (checks it is connected)
        # settings .......................................................................
        self._servo_min = -90.0        # Smallest position to use (n/90)
        self._servo_max = +90.0        # Largest position to use (n/90)
        self._startup_delay = 0.5      # Delay before making the initial move
        self._step_delay = 0.05        # Delay between steps
        self._rate_start = 0.05        # Step distance for all servos during initial move
        self._step_distance = 1.0      # Step distance for servo #1
        self._use_servo_1 = True
        self._enabled = True
        self._closed = False
        self._log.info('ready.')


    # ..........................................................................
    def sweep(self):
        '''
            Repeatedly sweeps between minimum and maximum until disabled.
        '''
        self._log.info('press CTRL+C to quit.')
        try:

            self._log.info('move to center position.')
            position = 0.0
            self.set_position(position)
            # wait to be sure the servo has caught up
            time.sleep(self._startup_delay)

            self._log.info('sweep to start position.')
            while position > self._servo_min:
                position -= self._rate_start
                if position < self._servo_min:
                    position = self._servo_min
                self.set_position(position)
                time.sleep(self._step_delay)

            self._log.info('sweep through the range.')
            while True:
                position += self._step_distance
                # check if too large, if so wrap to the over end
                if position > self._servo_max:
                    position -= (self._servo_max - self._servo_min)
                self.set_position(position)
                time.sleep(self._step_delay)

        except KeyboardInterrupt:
            self.close()
            self._log.info('done.')


    # ..........................................................................
    def set_position(self, position):
        '''
            Set the position of the servo to a value between -90.0 and 90.0 degrees.
            Values outside this range set to their respective min/max.
        '''
        if position < self._servo_min:
            self._log.warn('cannot set; position less than minimum: {}°'.format(position))
            position = self._servo_min
        if position > self._servo_max:
            self._log.warn('cannot set; position less than minimum: {}°'.format(position))
            position = self._servo_max
        self._log.debug('servo position: {}°'.format(position))
        # values for servo range from -1.0 to 1.0
        _value = position / 90.0
        if self._use_servo_1:
            self._UB.SetServoPosition1(_value)
        else:
            self._UB.SetServoPosition2(_value)


    # ..........................................................................
    def disable(self):
        self._enabled = False
        self._log.info('disabled.')


    # ..........................................................................
    def reset(self):
        if self._use_servo_1:
            self._UB.SetServoPosition1(0.0)
        else:
            self._UB.SetServoPosition2(0.0)
        self._log.info('reset position.')


    # ..........................................................................
    def close(self):
        '''
            Close the servo. If it has not already been disabled its position
            will reset to zero.
        '''
        if self._enabled:
            self.reset()
        if not self._closed:
            self._closed = True
            self.disable()
            self._log.info('closed.')


#EOF
