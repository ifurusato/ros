#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# Copyright 2020 by Murray Altheim. All rights reserved. This file is part of
# the Robot OS project and is released under the "Apache Licence, Version 2.0".
# Please see the LICENSE file included as part of this package.
#
# A quick test of the simple_pid library.

import sys, time
from colorama import init, Fore, Style
init()

from lib.logger import Logger, Level
from lib.config_loader import ConfigLoader

from lib.motors import Motors
from lib.enums import Orientation
from lib.gamepad import Gamepad
from lib.pid_ctrl import PIDController
from lib.ioe_pot import Potentiometer

# ..............................................................................
def main():

    _level = Level.INFO
    _log = Logger('main', _level)
    _loader = ConfigLoader(_level)
    _config = _loader.configure('config.yaml')

    try:
        _motors = Motors(_config, None, _level)
        _pot = Potentiometer(_config, Level.INFO)
        _pot.set_output_limits(0.0, 127.0) 

        # motor configuration: starboard, port or both?
        _orientation = Orientation.PORT

        _log.info(Fore.YELLOW + '================================================')

        if _orientation == Orientation.BOTH or _orientation == Orientation.PORT:
            _port_motor = _motors.get_motor(Orientation.PORT)
            _port_pid = PIDController(_config, _port_motor, level=Level.DEBUG)
            _port_pid.enable()

        if _orientation == Orientation.BOTH or _orientation == Orientation.STBD:
            _stbd_motor = _motors.get_motor(Orientation.STBD)
            _stbd_pid = PIDController(_config, _stbd_motor, level=Level.DEBUG)
            _stbd_pid.enable()

#       sys.exit(0)

        try:

            while True:
#               _value = _pot.get_value()
                _value = 127.0 - _pot.get_scaled_value()
                if _value > 125.0:
                    _value = 127.0
                _velocity = Gamepad.convert_range(_value)
                if _orientation == Orientation.BOTH or _orientation == Orientation.PORT:
                    _port_pid.velocity = _velocity * 100.0
                if _orientation == Orientation.BOTH or _orientation == Orientation.STBD:
                    _stbd_pid.velocity = _velocity * 100.0
                _log.info(Fore.GREEN + 'value: {:<5.2f}; velocity: {:5.2f}'.format(_value, _velocity))
                time.sleep(0.1)

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
        _log.info(Fore.RED + Style.BRIGHT + 'error in PID controller: {}'.format(e))
    finally:
        _log.info(Fore.YELLOW + Style.BRIGHT + 'C. finally.')


if __name__== "__main__":
    main()

#EOF
