#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# Copyright 2020 by Murray Altheim. All rights reserved. This file is part of
# the Robot OS project and is released under the "Apache Licence, Version 2.0".
# Please see the LICENSE file included as part of this package.
#

import sys, time, random
from threading import Thread
from colorama import init, Fore, Style
init()

from lib.enums import Direction, Orientation
from lib.slew import SlewRate
from lib.logger import Level, Logger
from lib.motors import Motor

class RoamBehaviour():
    '''
        This action class provides a roaming behaviour.
    '''
    def __init__(self, motors, level):
        self._log = Logger("roam", level)
        self._port_pid = motors._port_pid
        self._stbd_pid = motors._stbd_pid
        self._roam_port_complete = False
        self._roam_stbd_complete = False
        self._log.info('ready.')

    # ..........................................................................
    def _callback_port(self):
        self._log.info(Fore.RED   + 'port roam complete.')
        self._roam_port_complete = True

    # ..........................................................................
    def _callback_stbd(self):
        self._log.info(Fore.GREEN + 'stbd roam complete.')
        self._roam_stbd_complete = True

    # ..........................................................................
    def is_roaming(self):
        return not self._roam_port_complete and not self._roam_stbd_complete

    def _roam(self, velocity, direction, slew_rate, steps, callback, orientation):
        self._log.info('begin roaming...')
        for i in range(10):
            self._log.info(Fore.GREEN + 'roam [{:d}]'.format(i))
            if orientation is Orientation.PORT:
                self._port_pid.step_to(velocity, direction, slew_rate, steps)
            elif orientation is Orientation.STBD:
                self._stbd_pid.step_to(velocity, direction, slew_rate, steps)
            time.sleep(1.0)
        callback()
        self._log.info('stop roaming.')

    # ..........................................................................
    def roam(self):
        '''
            Begin roaming.
        '''
        self._log.info('roaming...')

        self._roam_port_complete = False
        self._roam_stbd_complete = False

        _forward_steps_per_rotation = 494
        _rotations = 2
        _forward_steps = _forward_steps_per_rotation * _rotations
        _velocity = 35.0 #Velocity.HALF
        _direction = Direction.FORWARD
        _slew_rate = SlewRate.SLOW
        self._log.info('start roaming at velocity: {}'.format(_velocity))
        _tp = Thread(target=self._roam, args=(_velocity, _direction, _slew_rate, _forward_steps, self._callback_port, Orientation.PORT))
        _ts = Thread(target=self._roam, args=(_velocity, _direction, _slew_rate, _forward_steps, self._callback_stbd, Orientation.STBD))
        _tp.start()
        _ts.start()
        _tp.join()
        _ts.join()
        self._log.info('complete.')


#EOF
