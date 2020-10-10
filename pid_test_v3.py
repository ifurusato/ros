#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# Copyright 2020 by Murray Altheim. All rights reserved. This file is part of
# the Robot OS project and is released under the "Apache Licence, Version 2.0".
# Please see the LICENSE file included as part of this package.
#
# A quick test of the simple_pid library.

import sys, time, traceback
from colorama import init, Fore, Style
init()

from lib.velocity import Velocity
from lib.logger import Logger, Level
from lib.config_loader import ConfigLoader

from lib.status import Status
from lib.motors_v2 import Motors
from lib.enums import Orientation
from lib.pot import Potentiometer 

from lib.pid_v4 import PIDController

# ..............................................................................
def main():

    _level = Level.INFO
    _log = Logger('main', _level)

    _adjust_velocity = True # otherwise kp or kd

    _loader = ConfigLoader(_level)
    filename = 'config.yaml'
    _config = _loader.configure(filename)
    _pot = Potentiometer(_config, _level)
    _status = Status(_config, _level)

    try:

        _status.enable()
        _motors = Motors(_config, None, _level)
        _port_motor = _motors.get_motor(Orientation.PORT)
        _stbd_motor = _motors.get_motor(Orientation.STBD)

        _port_pid = PIDController(_config, _port_motor, level=_level)
        _stbd_pid = PIDController(_config, _stbd_motor, level=_level)

        _value = _pot.get_scaled_value()
        if _adjust_velocity: # otherwise kp or kd
            _port_pid.velocity = _value
            _stbd_pid.velocity = _value
        else:
            _port_pid.velocity = 40.0
            _stbd_pid.velocity = 40.0
            _port_pid.kp = _value
            _stbd_pid.kp = _value
#           _stbd_pid.pid.kd = _value

        _port_pid.enable()
        _stbd_pid.enable()

        try:

            while True:
                _value = _pot.get_scaled_value()
                if _adjust_velocity: # otherwise kp or kd
                    _port_pid.velocity = _value
                    _stbd_pid.velocity = _value
                else:
                    _port_pid.kp = _value
                    _stbd_pid.kp = _value
#                   _stbd_pid.kd = _value

#               _log.info(Fore.BLACK + 'STBD setpoint={:>5.2f}.'.format(_stbd_pid.get_velocity()))
                time.sleep(0.1)

        except KeyboardInterrupt:
            _log.info(Fore.CYAN + Style.BRIGHT + 'PID test complete.')
        finally:
            _stbd_pid.disable()
            _motors.brake()
            _status.disable()

    except Exception as e:
        _log.info(Fore.RED + Style.BRIGHT + 'error in PID controller: {}'.format(e))
        traceback.print_exc(file=sys.stdout)
    finally:
        _log.info(Fore.YELLOW + Style.BRIGHT + 'C. finally.')


if __name__== "__main__":
    main()

#EOF
