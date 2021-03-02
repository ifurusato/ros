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

import time
from colorama import init, Fore, Style
init()

try:
    import numpy
except ImportError:
    exit("This script requires the numpy module\nInstall with: pip3 install --user numpy")

from lib.servo import Servo
from lib.logger import Logger, Level

# ..............................................................................
class UltrasonicScanner():

    def __init__(self, config, level):
        self._log = Logger('ultrasonic', Level.INFO)
        self._config = config
        if self._config:
            self._log.info('configuration provided.')
            _config = self._config['ros'].get('ultrasonic_scanner')
            self._min_angle = _config.get('min_angle')
            self._max_angle = _config.get('max_angle')
            self._degree_step = _config.get('degree_step')
            self._use_raw_distance = _config.get('use_raw_distance')
            self._read_delay_sec = _config.get('read_delay_sec')
            self._log.info('read delay: {:>4.1f} sec'.format(self._read_delay_sec))
            _servo_number = _config.get('servo_number')
        else:
            self._log.warning('no configuration provided.')
            self._min_angle = -60.0
            self._max_angle =  60.0
            self._degree_step = 3.0
            self._use_raw_distance = False
            self._read_delay_sec = 0.1
            _servo_number = 2

        self._log.info('scan from {:>5.2f} to {:>5.2f} with step of {:>4.1f}°'.format(self._min_angle, self._max_angle, self._degree_step))
        self._servo = Servo(self._config, _servo_number, level)
        self._ub = self._servo.get_ultraborg()
#       self._tof = TimeOfFlight(_range, Level.WARN)
        self._error_range = 0.067
        self._enabled = False
        self._closed = False
        self._log.info('ready.')

    # ..........................................................................
    def _in_range(self, p, q):
        return p >= ( q - self._error_range ) and p <= ( q + self._error_range )

    # ..........................................................................
    def scan(self):
        if not self._enabled:
            self._log.warning('cannot scan: disabled.')
            return

        start = time.time()
        _min_mm = 9999.0
        _angle_at_min = 0.0
        _max_mm = 0
        _angle_at_max = 0.0
        _max_retries = 10

        self._servo.set_position(self._min_angle)
        time.sleep(0.3)
        _slack = 0.1
        self._log.info(Fore.BLUE + Style.BRIGHT + 'scanning from {:>5.2f} to {:>5.2f} with step of {:>4.1f}°...'.format(self._min_angle, self._max_angle, self._degree_step))
        for degrees in numpy.arange(self._min_angle, self._max_angle + _slack, self._degree_step):
            self._log.debug('loop set to : {:>5.2f}°...'.format(degrees))
            if self._servo.is_in_range(degrees):
                self._servo.set_position(degrees)
                wait_count = 0
                while not self._in_range(self._servo.get_position(degrees), degrees) and wait_count < 10:
                    time.sleep(0.0025)
                    wait_count += 1
                self._log.debug(Fore.GREEN + Style.BRIGHT + 'measured degrees: {:>5.2f}°: \ttarget: {:>5.2f}°; waited: {:d}'.format(\
                        self._servo.get_position(degrees), degrees, wait_count))
                _mm = self._servo.get_distance(_max_retries, self._use_raw_distance)
                # if we get a zero we keep trying...
                if _mm is None:
                    self._log.info('failed to read distance at {:>5.2f}°.'.format(degrees))
                else:
                    if _mm <= 0.01:
                        retry_count = 0
                        while _mm == 0.0 and retry_count < _max_retries:
                            _mm = self._servo.get_distance(_max_retries, self._use_raw_distance)
                            if _mm is None:
                                self._log.info('failed to read distance at {:>5.2f}°: '.format(degrees) + Fore.RED + '\t retries: {:d}'.format(retry_count))
                            else:
                                if _mm <= 0.01:
                                    self._log.info('distance at {:>5.2f}°: '.format(degrees) + Fore.RED + '\t{:>6.0f}mm'.format(_mm) + '\t retries: {:d}'.format(retry_count))
                                else:
                                    self._log.info('distance at {:>5.2f}°: \t{:>6.0f}mm'.format(degrees, _mm) + Fore.BLACK + ' (on retry)')
                            retry_count += 1
                            time.sleep(0.1)
                    else:
                        self._log.info('distance at {:>5.2f}°: \t{:>6.0f}mm'.format(degrees, _mm))
                    if _mm is not None:
                        # capture min and max at angles
                        _min_mm = min(_min_mm, _mm)
                        if _mm == _min_mm:
                            _angle_at_min = degrees
                        _max_mm = max(_max_mm, _mm)
                        if _mm == _max_mm:
                            _angle_at_max = degrees
                    time.sleep(self._read_delay_sec)
#                   time.sleep(0.1)
            else:
                self._log.warning('requested position: {:>5.2f}° out range of servo movement.'.format(degrees))

        time.sleep(0.1)
#           self._log.info('complete.')
        elapsed = time.time() - start
        self._log.info('scan complete: {:>5.2f}sec elapsed.'.format(elapsed))

        self._log.info(Fore.CYAN + Style.BRIGHT + 'mix. distance at {:>5.2f}°:\t{}mm'.format(_angle_at_min, _min_mm))
        self._log.info(Fore.CYAN + Style.BRIGHT + 'max. distance at {:>5.2f}°:\t{}mm'.format(_angle_at_max, _max_mm))
        self._servo.set_position(0.0)
        return [ _angle_at_min, _min_mm, _angle_at_max, _max_mm ]

    # ..........................................................................
    def enable(self):
        if self._closed:
            self._log.warning('cannot enable: closed.')
            return
#       self._tof.enable()
        self._enabled = True

    # ..........................................................................
    def disable(self):
        self._enabled = False
        self._servo.disable()
#       self._tof.disable()

    # ..........................................................................
    def close(self):
        self.disable()
        self._servo.close()
        self._closed = True

#EOF
