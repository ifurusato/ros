#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# Copyright 2020 by Murray Altheim. All rights reserved. This file is part of
# the Robot OS project and is released under the "Apache Licence, Version 2.0".
# Please see the LICENSE file included as part of this package.
#

import sys, time, random, threading
from colorama import init, Fore, Style
init()

from lib.enums import Speed, Orientation
from lib.logger import Level, Logger
from lib.motors import Motor
from lib.ifs import IntegratedFrontSensor
from lib.rgbmatrix import RgbMatrix, Color, DisplayType

class Behaviours():
    '''
        This class provides avoidance and some other relatively simple behaviours.
    '''
    def __init__(self, motors, ifs, level):
        self._log = Logger("avoid", level)
        self._motors = motors
        self._ifs = ifs
        self._rgbmatrix = RgbMatrix(Level.INFO)
        self._fast_speed = 99.0
        self._slow_speed = 50.0
        self._log.info('ready.')

    # ..........................................................................
    def back_up(self, duration_sec):
        '''
            Back up for the specified duration so we don't hang our bumper.
        '''
        self._motors.astern(self._fast_speed)
        time.sleep(duration_sec)

    # avoid ....................................................................
    def avoid(self, orientation):
        '''
            Avoids differently depending on orientation.           
        '''
        self._log.info(Fore.CYAN + 'avoid {}.'.format(orientation.name))
        
        if orientation is Orientation.CNTR:
            orientation = Orientation.PORT if random.choice((True, False)) else Orientation.STBD
            self._log.info(Fore.YELLOW + 'randomly avoiding to {}.'.format(orientation.name))

        self._ifs.suppress(True)
        self._motors.halt()
        self.back_up(0.5)
        if orientation is Orientation.PORT:
            self._motors.spin_port(self._fast_speed)
        elif orientation is Orientation.STBD:
            self._motors.spin_starboard(self._fast_speed)
        else:
            raise Exception('unexpected center orientation.')
        time.sleep(2.0)
        self._motors.brake()
        self._ifs.suppress(False)

        self._log.info('action complete: avoid.')

    # sniff ....................................................................
    def sniff(self):
        if self._rgbmatrix.is_disabled():
            self._rgbmatrix.set_solid_color(Color.BLUE)
            self._rgbmatrix.set_display_type(DisplayType.SOLID)
#           self._rgbmatrix.set_display_type(DisplayType.RANDOM)
            self._rgbmatrix.enable()
        else:
            self._rgbmatrix.disable()

#EOF
