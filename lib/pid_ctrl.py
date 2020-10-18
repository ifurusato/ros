#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# Copyright 2020 by Murray Altheim. All rights reserved. This file is part of
# the Robot Operating System project and is released under the "Apache Licence,
# Version 2.0". Please see the LICENSE file included as part of this package.
#
# author:   Murray Altheim
# created:  2020-08-08
# modified: 2020-10-18
#

from colorama import init, Fore, Style
init()

#from lib.config_loader import ConfigLoader
from lib.logger import Logger, Level
from lib.enums import Orientation
from lib.motors_v2 import Motors
from lib.pid_v4 import PIDController

# ..............................................................................
class PIDMotorController():
    def __init__(self, config, motors, level):
        super().__init__()
        self._motors = motors
        self._port_pid = PIDController(config, motors.get_motor(Orientation.PORT), level=level)
        self._stbd_pid = PIDController(config, motors.get_motor(Orientation.STBD), level=level)
#       self._port_pid.enable()
#       self._stbd_pid.enable()

    # ..........................................................................
    def get_pid_controllers(self):
        return self._port_pid, self._stbd_pid

    # ..........................................................................
    def _monitor(self, f_is_enabled):
        '''
            A 20Hz loop that prints PID statistics to the log while enabled. Note that this loop
            is not synchronised with the two PID controllers, which each have their own loop.
        '''
        _rate = Rate(20)
        while f_is_enabled():
            kp, ki, kd, p_cp, p_ci, p_cd, p_last_power, p_current_motor_power, p_power, p_current_velocity, p_setpoint, p_steps = self._port_pid.stats
            _x, _y, _z, s_cp, s_ci, s_cd, s_last_power, s_current_motor_power, s_power, s_current_velocity, s_setpoint, s_steps = self._stbd_pid.stats
            _msg = ('{:7.4f}|{:7.4f}|{:7.4f}|{:7.4f}|{:7.4f}|{:7.4f}|{:5.2f}|{:5.2f}|{:5.2f}|{:<5.2f}|{:>5.2f}|{:d}|{:7.4f}|{:7.4f}|{:7.4f}|{:5.2f}|{:5.2f}|{:5.2f}|{:<5.2f}|{:>5.2f}|{:d}|').format(\
                    kp, ki, kd, p_cp, p_ci, p_cd, p_last_power, p_current_motor_power, p_power, p_current_velocity, p_setpoint, p_steps, \
                    s_cp, s_ci, s_cd, s_last_power, s_current_motor_power, s_power, s_current_velocity, s_setpoint, s_steps)
            _p_hilite = Style.BRIGHT if p_power > 0.0 else Style.NORMAL
            _s_hilite = Style.BRIGHT if s_power > 0.0 else Style.NORMAL
            _msg2 = (Fore.RED+_p_hilite+'{:7.4f}|{:7.4f}|{:7.4f}|{:<5.2f}|{:<5.2f}|{:<5.2f}|{:>5.2f}|{:d}'+Fore.GREEN+_s_hilite+'|{:7.4f}|{:7.4f}|{:7.4f}|{:5.2f}|{:5.2f}|{:<5.2f}|{:<5.2f}|{:d}|').format(\
                    p_cp, p_ci, p_cd, p_last_power, p_power, p_current_velocity, p_setpoint, p_steps, \
                    s_cp, s_ci, s_cd, s_last_power, s_power, s_current_velocity, s_setpoint, s_steps)
            _rate.wait()
            self._file_log.file(_msg)
            self._log.info(_msg2)
        self._log.info('PID monitor stopped.')

    # ..........................................................................
    @property
    def enabled(self):
        return self._port_pid.enabled or self._stbd_pid.enabled

    # ..........................................................................
    def enable(self):
        self._port_pid.enable()
        self._stbd_pid.enable()

    # ..........................................................................
    def disable(self):
        self._motors.disable()
        self._port_pid.disable()
        self._stbd_pid.disable()

    # ..........................................................................
    def close(self):
        self._motors.close()
        self._port_pid.close()
        self._stbd_pid.close()

#EOF
