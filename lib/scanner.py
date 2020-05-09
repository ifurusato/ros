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
from lib.servo import Servo
from lib.logger import Logger, Level
from lib.player import Sound, Player

# ..............................................................................
class Scanner():

    def __init__(self, config, player, level):
        self._log = Logger('scanner', Level.INFO)
        self._player = player
        self._servo = Servo(Level.WARN)
        _range = Range.PERFORMANCE
#       _range = Range.LONG
#       _range = Range.MEDIUM
#       _range = Range.SHORT
        self._min_angle = -60.0
        self._max_angle =  60.0
        self._degree_step = 2.0
        self._tof = TimeOfFlight(_range, Level.WARN)
        self._enabled = False
        self._closed = False
        self._log.info('ready.')


    # ..........................................................................
    def scan(self):
        if not self._enabled:
            self._log.warning('cannot scan: disabled.')
            return
        try:
    
            start = time.time()
            _max_mm = 0
            _max_angle = 0.0
            self._player.repeat(Sound.PING, 3, 0.1)
            for degrees in numpy.arange(self._min_angle, self._max_angle, self._degree_step):
                self._servo.set_position(degrees)
                mm = self._tof.read_distance()
                _max_mm = max(_max_mm, mm)
                if mm == _max_mm:
                    _max_angle = degrees
                self._log.info('distance at {:>5.2f}°: \t{}mm'.format(degrees, mm))
                time.sleep(0.001)
            self._player.stop()
            time.sleep(0.1)
#           self._log.info('complete.')
            elapsed = time.time() - start
            self._log.info('scan complete: {:>5.2f}sec elapsed.'.format(elapsed))

            self._log.info('max. distance at {:>5.2f}°:\t{}mm'.format(_max_angle, _max_mm))
            self._servo.set_position(0.0)
#           self._servo.set_position(_max_angle)
#           self.close()
            return [ _max_angle, _max_mm ]
    
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
        self._servo.disable()
        self._tof.disable()


    # ..........................................................................
    def close(self):
        self.disable()
        self._servo.close()
        self._closed = True


#EOF
