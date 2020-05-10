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

from lib.servo import Servo
from lib.logger import Logger, Level
from lib.player import Sound, Player

# ..............................................................................
class UltrasonicScanner():

    def __init__(self, config, level):
        self._log = Logger('uscanner', Level.INFO)
        self._config = config
        if self._config:
            self._log.info('configuration provided.')
            _config = self._config['ros'].get('ultrasonic_scanner')
            self._min_angle = _config.get('min_angle')
            self._max_angle = _config.get('max_angle')
            self._degree_step = _config.get('degree_step')  
        else:
            self._log.warning('no configuration provided.')
            self._min_angle = -60.0
            self._max_angle =  60.0
            self._degree_step = 3.0

        self._log.info('scan from {:>5.2f} to {:>5.2f} with step of {:>4.1f}°'.format(self._min_angle, self._max_angle, self._degree_step))
        _servo_number = 2
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
        try:
    
            start = time.time()
            _min_mm = 9999.0
            _angle_at_min = 0.0
            _max_mm = 0
            _angle_at_max = 0.0

            self._servo.set_position(self._min_angle)
            time.sleep(0.3)

            for degrees in numpy.arange(self._min_angle, self._max_angle + 0.1, self._degree_step):
                self._servo.set_position(degrees)
                wait_count = 0
                while not self._in_range(self._servo.get_position(degrees), degrees) and wait_count < 10:
                    time.sleep(0.0025)
                    wait_count += 1
                self._log.debug(Fore.GREEN + Style.BRIGHT + 'measured degrees: {:>5.2f}°: \ttarget: {:>5.2f}°; waited: {:d}'.format(\
                        self._servo.get_position(degrees), degrees, wait_count))
                mm = self._servo.get_distance()
                self._log.info('distance at {:>5.2f}°: \t{}mm'.format(degrees, mm))
                # capture min and max at angles
                _min_mm = min(_min_mm, mm)
                if mm == _min_mm:
                    _angle_at_min = degrees
                _max_mm = max(_max_mm, mm)
                if mm == _max_mm:
                    _angle_at_max = degrees
                time.sleep(0.1)

            time.sleep(0.1)
#           self._log.info('complete.')
            elapsed = time.time() - start
            self._log.info('scan complete: {:>5.2f}sec elapsed.'.format(elapsed))

            self._log.info(Fore.CYAN + Style.BRIGHT + 'mix. distance at {:>5.2f}°:\t{}mm'.format(_angle_at_min, _min_mm))
            self._log.info(Fore.CYAN + Style.BRIGHT + 'max. distance at {:>5.2f}°:\t{}mm'.format(_angle_at_max, _max_mm))
            self._servo.set_position(0.0)
#           self._servo.set_position(_angle_at_max)
#           self.close()
            return [ _angle_at_min, _min_mm, _angle_at_max, _max_mm ]
    
        except KeyboardInterrupt:
            self._log.info('caught Ctrl-C.')
            self.close()
            self._log.info('interrupted: incomplete.')
    

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
