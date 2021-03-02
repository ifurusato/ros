#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# Copyright 2020-2021 by Murray Altheim. All rights reserved. This file is part
# of the Robot Operating System project, released under the MIT License. Please
# see the LICENSE file included as part of this package.
#
# author:   Murray Altheim
# created:  2020-10-12
# modified: 2020-10-12
#

import sys, time, traceback
import numpy
from colorama import init, Fore, Style
init()

from lib.logger import Logger, Level
from lib.config_loader import ConfigLoader

from lib.motors import Motors
from lib.enums import Orientation
from lib.gamepad import Gamepad
from lib.pid_ctrl import PIDController
from lib.ioe_pot import Potentiometer
from lib.rate import Rate

# ..............................................................................
def main():

    _level = Level.INFO
    _log = Logger('main', _level)
    _loader = ConfigLoader(_level)
    _config = _loader.configure('config.yaml')

    try:
        _motors = Motors(_config, None, Level.WARN)
        _pot = Potentiometer(_config, Level.WARN)
        _pot.set_output_limits(0.0, 127.0) 

        # motor configuration: starboard, port or both?
        _orientation = Orientation.BOTH

        if _orientation == Orientation.BOTH or _orientation == Orientation.PORT:
            _port_motor = _motors.get_motor(Orientation.PORT)
            _port_pid = PIDController(_config, _port_motor, level=Level.WARN)
            _port_pid.enable()

        if _orientation == Orientation.BOTH or _orientation == Orientation.STBD:
            _stbd_motor = _motors.get_motor(Orientation.STBD)
            _stbd_pid = PIDController(_config, _stbd_motor, level=Level.WARN)
            _stbd_pid.enable()

        ROTATE = True
        _rotate = -1.0 if ROTATE else 1.0
     
#       sys.exit(0)
        _stbd_velocity = 0.0
        _port_velocity = 0.0

        _step =  0.5
        _min  =  0.0
        _max  = 70.0
        _rate = Rate(10)

        try:

#           for _value in numpy.arange(_min, _max, _step):
            while True:
                # update RGB LED
#               _pot.set_rgb(_pot.get_value())
                _value = 127.0 - _pot.get_scaled_value(True)
                if _value > 125.0:
                    _value = 127.0
                _velocity = Gamepad.convert_range(_value)
                if _orientation == Orientation.BOTH or _orientation == Orientation.PORT:
                    _port_pid.setpoint = _velocity * 100.0
                    _port_velocity = _port_pid.setpoint
                if _orientation == Orientation.BOTH or _orientation == Orientation.STBD:
                    _stbd_pid.setpoint = _rotate * _velocity * 100.0
                    _stbd_velocity = _stbd_pid.setpoint
                _log.info(Fore.WHITE + 'value: {:<5.2f}; set-point: {:5.2f}; velocity: '.format(_value, _velocity) \
                        + Fore.RED   + ' port: {:5.2f}\t'.format(_port_velocity) + Fore.GREEN + ' stbd: {:5.2f}'.format(_stbd_velocity))
                _rate.wait()

            _log.info(Fore.YELLOW + 'resting...')
            time.sleep(10.0)

#           for _value in numpy.arange(_min, _max, _step):
            while True:
                # update RGB LED
#               _pot.set_rgb(_pot.get_value())
                _value = 127.0 - _pot.get_scaled_value(True)
                if _value > 125.0:
                    _value = 127.0
                _velocity = Gamepad.convert_range(_value)
                if _orientation == Orientation.BOTH or _orientation == Orientation.PORT:
                    _port_pid.setpoint = _rotate * _velocity * 100.0
                    _port_velocity = _port_pid.setpoint
                if _orientation == Orientation.BOTH or _orientation == Orientation.STBD:
                    _stbd_pid.setpoint = _velocity * 100.0
                    _stbd_velocity = _stbd_pid.setpoint
                _log.info(Fore.MAGENTA + 'value: {:<5.2f}; set-point: {:5.2f}; velocity: '.format(_value, _velocity) \
                        + Fore.RED   + ' port: {:5.2f}\t'.format(_port_velocity) + Fore.GREEN + ' stbd: {:5.2f}'.format(_stbd_velocity))
                _rate.wait()

            _log.info(Fore.YELLOW + 'end of cruising.')

        except KeyboardInterrupt:
            _log.info(Fore.CYAN + Style.BRIGHT + 'PID test complete.')
        finally:
            if _orientation == Orientation.BOTH or _orientation == Orientation.PORT:
                _port_pid.disable()
            if _orientation == Orientation.BOTH or _orientation == Orientation.STBD:
                _stbd_pid.disable()
            _motors.brake()

    except Exception as e:
        _log.info(Fore.RED + Style.BRIGHT + 'error in PID controller: {}\n{}'.format(e, traceback.format_exc()))

    finally:
        _log.info(Fore.YELLOW + Style.BRIGHT + 'C. finally.')


if __name__== "__main__":
    main()

#EOF
