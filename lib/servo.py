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
from colorama import init, Fore, Style
init()

from lib.logger import Level, Logger

class Servo():
    '''
        Provided with configuration this permits setting of the center position offset.

        The UltraBorg supports four servos, numbered 1-4.
    '''
    def __init__(self, config, number, level):
        self._number = number
        self._log = Logger("servo-{:d}".format(number), level)
        self._config = config
        if self._config:
            self._log.info('configuration provided.')
            _config = self._config['ros'].get('servo{:d}'.format(number))
            self._center_offset = _config.get('center_offset')
        else:
            self._log.warning('no configuration provided.')
            self._center_offset = 0.0
        self._log.info('center offset: {:>3.1f}'.format(self._center_offset))

        self._UB = UltraBorg(level)    # create a new UltraBorg object
        self._UB.Init()                # initialise the board (checks it is connected)
        # settings .......................................................................
        self._min_angle = -90.1        # Smallest position to use (n/90)
        self._max_angle = +90.1        # Largest position to use (n/90)
        self._startup_delay = 0.5      # Delay before making the initial move
        self._step_delay = 0.05        # Delay between steps
        self._rate_start = 0.05        # Step distance for all servos during initial move
        self._step_distance = 1.0      # Step distance for servo #1
        self._enabled = False
        self._closed = False
        self._log.info('ready.')

    # ..........................................................................
    def get_min_angle(self):
        '''
            Return the configured minimum servo angle.
        '''
        return self._min_angle

    # ..........................................................................
    def get_max_angle(self):
        '''
            Return the configured maximum servo angle.
        '''
        return self._max_angle

    # ..........................................................................
    def is_in_range(self, degrees):
        '''
            A convenience method that returns true if the argument is within the
            minimum and maximum range (inclusive of endpoints) of the servo.
        '''
        return degrees >= self._min_angle and degrees <= self._max_angle

    # ..........................................................................
    def set_position(self, position):
        '''
            Set the position of the servo to a value between -90.0 and 90.0 degrees.
            Values outside this range set to their respective min/max.

            This adjusts the argument by the value of the center offset.
        '''
        self._log.debug('set servo position to: {:+5.2f}° (center offset {:+5.2f}°)'.format(position, self._center_offset))
        position += self._center_offset
        if position < self._min_angle:
            self._log.warning('cannot set position {:+5.2f}° less than minimum {:+5.2f}°'.format(position, self._min_angle))
            position = self._min_angle
        if position > self._max_angle:
            self._log.warning('cannot set position {:+5.2f}° greater than maximum {:+5.2f}°'.format(position, self._max_angle))
            position = self._max_angle
        # values for servo range from -1.0 to 1.0
        _value = position / 90.0
        if self._number == 1:
            self._UB.SetServoPosition1(_value)
        elif self._number == 2:
            self._UB.SetServoPosition2(_value)
        elif self._number == 3:
            self._UB.SetServoPosition3(_value)
        elif self._number == 4:
            self._UB.SetServoPosition4(_value)

    # ..........................................................................
    def get_position(self, defaultValue):
        '''
            Get the position of the servo. If unavailable return the default. 
        '''
        if self._number == 1:
            _position = self._UB.GetServoPosition1()
        elif self._number == 2:
            _position = self._UB.GetServoPosition2()
        elif self._number == 3:
            _position = self._UB.GetServoPosition3()
        elif self._number == 4:
            _position = self._UB.GetServoPosition4()
        if _position is None:
            return defaultValue
        else:
            return ( _position * 90.0 ) + self._center_offset

    # ..........................................................................
    def get_distance(self, retry_count, useRawDistance):
        '''
            Gets the filtered distance for the ultrasonic module in millimeters.
            Parameters:
                retry_count: how many times to attempt to read from the sensor
                             before giving up (this value is ignored when 
                             useRawDistance is True)
                useRawDistance: if you need a faster response use this instead 
                             (no filtering) e.g.:
                                 0     -> No object in range
                                 25    -> Object 25 mm away
                                 1000  -> Object 1000 mm (1 m) away
                                 3500  -> Object 3500 mm (3.5 m) away

            Returns 0 for no object detected or no ultrasonic module attached.

            This admittedly is not a servo function but since we have an UltraBorg
            supporting this servo, this becomes a convenience method. The ultrasonic
            sensor should be connected to the same number as the servo.
        '''
        if self._number == 1:
            if useRawDistance:
                return self._UB.GetRawDistance1()
            else:
                return self._UB.GetWithRetry(self._UB.GetDistance1, retry_count)
        elif self._number == 2:
            if useRawDistance:
                return self._UB.GetRawDistance2()
            else:
                return self._UB.GetWithRetry(self._UB.GetDistance2, retry_count)
        elif self._number == 3:
            if useRawDistance:
                return self._UB.GetRawDistance3()
            else:
                return self._UB.GetWithRetry(self._UB.GetDistance3, retry_count)
        elif self._number == 4:
            if useRawDistance:
                return self._UB.GetRawDistance4()
            else:
                return self._UB.GetWithRetry(self._UB.GetDistance4, retry_count)

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
            while position > self._min_angle:
                position -= self._rate_start
                if position < self._min_angle:
                    position = self._min_angle
                self.set_position(position)
                time.sleep(self._step_delay)

            self._log.info('sweep through the range.')
            while self._enabled:
                position += self._step_distance
                # check if too large, if so wrap to the over end
                if position > self._max_angle:
                    position -= (self._max_angle - self._min_angle)
                self.set_position(position)
                time.sleep(self._step_delay)

        except KeyboardInterrupt:
            self.close()
            self._log.info('done.')

    # ..........................................................................
    def get_ultraborg(self):
        '''
            Return the UltraBorg supporting this Servo.
        '''
        return self._UB

    # ..........................................................................
    def enable(self):
        self._enabled = True
        self._log.info('enabled.')

    # ..........................................................................
    def disable(self):
        self._enabled = False
        self._log.info('disabled.')

    # ..........................................................................
    def reset(self):
        if self._number == 1:
            self._UB.SetServoPosition1(0.0)
        elif self._number == 2:
            self._UB.SetServoPosition2(0.0)
        elif self._number == 3:
            self._UB.SetServoPosition3(0.0)
        elif self._number == 4:
            self._UB.SetServoPosition4(0.0)
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
