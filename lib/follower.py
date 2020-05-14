#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# Copyright 2020 by Murray Altheim. All rights reserved. This file is part of
# the Robot OS project and is released under the "Apache Licence, Version 2.0".
# Please see the LICENSE file included as part of this package.
#
# author:   altheim
# created:  2020-03-31
# modified: 2020-03-31

# Import library functions we need
import time
from colorama import init, Fore, Style
init()

try:
    import numpy
except ImportError:
    exit("This script requires the numpy module\nInstall with: sudo pip3 install numpy")

from lib.tof import TimeOfFlight, Range
from lib.enums import Orientation
from lib.servo import Servo
from lib.logger import Logger, Level

# ..............................................................................
class WallFollower():

    def __init__(self, config, level):
        self._log = Logger('follower', Level.INFO)
        self._config = config
        if self._config:
            self._log.info('configuration provided.')
            _config = self._config['ros'].get('wall_follower')
            self._port_angle = _config.get('port_angle')
            self._stbd_angle = _config.get('starboard_angle')
            _range_value = _config.get('tof_range')  
            _range = Range.from_str(_range_value)
            _servo_number = _config.get('servo_number')  
        else:
            self._log.warning('no configuration provided.')
            self._port_angle = -90.0
            self._stbd_angle =  90.0
            _range = Range.PERFORMANCE
            _servo_number = 2
#           _range = Range.LONG
#           _range = Range.MEDIUM
#           _range = Range.SHORT

        self._log.info('wall follower port angle: {:>5.2f}°; starboard angle: {:>5.2f}°'.format(self._port_angle, self._stbd_angle))
        self._servo = Servo(self._config, _servo_number, level)
        self._tof = TimeOfFlight(_range, Level.WARN)
        self._max_retries = 10
        self._enabled = False
        self._closed = False
        self._log.info('ready.')


    # ..........................................................................
    def scan(self):
        mm = 0.0
        wait_count = 0
        while mm <= 0.1 and wait_count < self._max_retries:
            mm = self._tof.read_distance()
            time.sleep(0.0025)
            wait_count += 1
        self._log.info('distance: {:>5.0f}mm'.format(mm))
        return mm


    # ..........................................................................
    def set_position(self, orientation):
        if not self._enabled:
            self._log.warning('cannot scan: disabled.')
            return
        if orientation == Orientation.PORT:
            self._servo.set_position(self._port_angle)
        elif orientation == Orientation.STBD:
            self._servo.set_position(self._stbd_angle)
        else:
            raise ValueError('only port or starboard acceptable for wall follower orientation')
        self._log.info('wall follower position set to {}.'.format(orientation))
    

    # ..........................................................................
    def enable(self):
        if self._closed:
            self._log.warning('cannot enable: closed.')
            return
        self._tof.enable()
        self._enabled = True


    # ..........................................................................
    def disable(self):
        self._enabled = False
        self._servo.set_position(0.0)
        self._servo.disable()
        self._tof.disable()


    # ..........................................................................
    def close(self):
        self.disable()
        self._servo.close()
        self._closed = True


#EOF
