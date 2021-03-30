#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# Copyright 2020-2021 by Murray Altheim. All rights reserved. This file is part
# of the Robot Operating System project, released under the MIT License. Please
# see the LICENSE file included as part of this package.
#
# author:   altheim
# created:  2020-03-31
# modified: 2021-03-29
#

import time
from datetime import datetime as dt
from colorama import init, Fore, Style
init()

try:
    import numpy
except ImportError:
    exit("This script requires the numpy module\nInstall with: pip3 install --user numpy")

from lib.tof import TimeOfFlight, Range
from lib.servo import Servo
from lib.logger import Logger, Level

# ..............................................................................
class Lidar():
    '''
    A combination of a VL53L1X laser distance sensor and a micro servo as a LIDAR.

    The zero position is straight forward, with negative (minimum servo position)
    sweeping to port, positive (maximum servo position) to starboard.

    The 'reverse_movement' parameter is used in case the servo movement is backwards.
    '''
    def __init__(self, config, level):
        self._log = Logger('lidar', Level.INFO)
        self._config = config
        if self._config:
            self._log.info('configuration provided.')
            _config = self._config['ros'].get('lidar')
            self._reverse_movement = _config.get('reverse_movement')
            self._double_sweep = _config.get('double_sweep')
            self._min_angle = _config.get('min_angle')
            self._max_angle = _config.get('max_angle')
            self._degree_step = _config.get('degree_step')
            self._step_delay_sec = _config.get('step_delay_sec')
            _range_value = _config.get('tof_range')
            _range = Range.from_str(_range_value)
            _servo_number = _config.get('servo_number')
        else:
            self._log.warning('no configuration provided.')
            self._log.info('play sound disabled.')
            self._reverse_movement = False
            self._double_sweep = False
            self._min_angle = -60.0
            self._max_angle =  60.0
            self._degree_step = 3.0
            self._step_delay_sec = 0.01
            _range = Range.PERFORMANCE
#           _range = Range.LONG
#           _range = Range.MEDIUM
#           _range = Range.SHORT
            _servo_number = -1

        self._log.info('scan range of {} from {:>4.1f}° to {:>4.1f}° with step of {:>4.1f}°'.format(_range, self._min_angle, self._max_angle, self._degree_step))
        if _servo_number > 0:
            self._servo = Servo(self._config, _servo_number, level)
        else:
            self._servo = None

        _range = Range.PERFORMANCE
#       _range = Range.LONG
#       _range = Range.MEDIUM
#       _range = Range.SHORT

        self._tof = TimeOfFlight(_range, Level.WARN)
        self._error_range = 0.067
        self._enabled = False
        self._closed = False
        self._log.info('ready.')

    # ..........................................................................
    def _in_range(self, p, q):
        return p >= ( q - self._error_range ) and p <= ( q + self._error_range )

    # ..........................................................................
    def _set_servo_position(self, angle):
        if self._servo:
            if self._reverse_movement:
                self._servo.set_position(-1.0 * angle)
            else:
                self._servo.set_position(angle)

    # ..........................................................................
    def _get_servo_position(self, default_angle):
        if self._servo:
            if self._reverse_movement:
                return -1.0 * self._servo.get_position(-1.0 * default_angle)
            else:
                return self._servo.get_position(default_angle)

    # ..........................................................................
    def scan(self):
        if not self._enabled:
            self._log.warning('cannot scan: disabled.')
            return None
        try:
            if self._servo:
                start = time.time()
                _min_mm = 9999.0
                _angle_at_min = 0.0
                _max_mm = 0
                _angle_at_max = 0.0
    
                self._set_servo_position(self._min_angle)
                time.sleep(0.3)
#               wait_count = 0
#               while ( not self._in_range(self._get_servo_position(self._min_angle), self._min_angle) ) and ( wait_count < 20 ):
#                   wait_count += 1
#                   self._set_servo_position(self._min_angle)
#                   self._log.info(Fore.MAGENTA + Style.BRIGHT + 'waiting for match at degrees: {:>5.2f}°: waited: {:d}'.format(self._get_servo_position(-1), wait_count))
#                   time.sleep(1.0)
#               time.sleep(0.05)
#               self._log.info(Fore.YELLOW + Style.BRIGHT + 'starting scan from degrees: {:>5.2f}°: waited: {:d}'.format(self._get_servo_position(-1), wait_count))
    
                # sweep from minimum to maximum ........................................................
                self._log.info('sweep fore...')
#               self._log.info('sweep min to max...')
                for degrees in numpy.arange(self._min_angle, self._max_angle + 0.01, self._degree_step):
                    self._set_servo_position(degrees)
                    wait_count = 0
                    while not self._in_range(self._get_servo_position(degrees), degrees) and wait_count < 10:
                        time.sleep(0.0025)
                        wait_count += 1
                    self._log.debug(Fore.GREEN + Style.BRIGHT + 'measured degrees: {:>5.2f}°: \ttarget: {:>5.2f}°; waited: {:d}'.format(\
                            self._get_servo_position(degrees), degrees, wait_count))
                    mm = self._tof.read_distance()
                    self._log.info('distance at {:>5.2f}°: \t{}mm'.format(degrees, mm))
                    # capture min and max at angles
                    _min_mm = min(_min_mm, mm)
                    if mm == _min_mm:
                        _angle_at_min = degrees
                    _max_mm = max(_max_mm, mm)
                    if mm == _max_mm:
                        _angle_at_max = degrees
                    time.sleep(self._step_delay_sec)
    
                if self._double_sweep:
                    self._log.info('sweep back...')
#                   self._log.info('sweep max to min...')
                    # sweep from maximum to minimum ........................................................
                    for degrees in numpy.arange(self._max_angle, self._min_angle + 0.01, -1.0 * self._degree_step):
                        self._set_servo_position(degrees)
                        wait_count = 0
                        while not self._in_range(self._get_servo_position(degrees), degrees) and wait_count < 10:
                            time.sleep(0.0025)
                            wait_count += 1
                        self._log.debug(Fore.GREEN + Style.BRIGHT + 'measured degrees: {:>5.2f}°: \ttarget: {:>5.2f}°; waited: {:d}'.format(\
                                self._get_servo_position(degrees), degrees, wait_count))
                        mm = self._tof.read_distance()
                        self._log.info('distance at {:>5.2f}°: \t{}mm'.format(degrees, mm))
                        # capture min and max at angles
                        _min_mm = min(_min_mm, mm)
                        if mm == _min_mm:
                            _angle_at_min = degrees
                        _max_mm = max(_max_mm, mm)
                        if mm == _max_mm:
                            _angle_at_max = degrees
                        time.sleep(self._step_delay_sec)
    
                time.sleep(0.1)
    #           self._log.info('complete.')
                elapsed = time.time() - start
                self._log.info('min. distance at {:>5.2f}°:\t{}mm'.format(_angle_at_min, _min_mm))
                self._log.info('max. distance at {:>5.2f}°:\t{}mm'.format(_angle_at_max, _max_mm))
                self._log.info('scan complete: {:>5.2f}sec elapsed.'.format(elapsed))
                self._set_servo_position(0.0)
    #           self._servo.set_position(_angle_at_max)
    #           self.close()
                return [ _angle_at_min, _min_mm, _angle_at_max, _max_mm ]
            else:
                _degrees = 0
                _start = dt.now()
                mm = self._tof.read_distance()
                _elapsed_ms = (dt.now() - _start).total_seconds() * 1000.0
                self._log.info('distance at {:>5.2f}°: \t{}mm'.format(_degrees, mm))
                self._log.info('scan complete: {:>5.2f}ms elapsed.'.format(_elapsed_ms))
                return [ -1.0, mm, -1.0, mm ]
        except KeyboardInterrupt:
            self._log.info('caught Ctrl-C.')
            self.close()
            self._log.info('interrupted: incomplete.')

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
        if self._servo:
            self._servo.disable()
        self._tof.disable()

    # ..........................................................................
    def close(self):
        self.disable()
        if self._servo:
            self._servo.close()
        self._closed = True

#EOF
