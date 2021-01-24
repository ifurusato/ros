#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# Copyright 2020 by Murray Altheim. All rights reserved. This file is part of
# the Robot OS project and is released under the "Apache Licence, Version 2.0".
# Please see the LICENSE file included as part of this package.
#
# A quick test of the simple_pid library.

import sys, time, numpy, traceback
from colorama import init, Fore, Style
init()

from lib.logger import Logger, Level
from lib.config_loader import ConfigLoader

from lib.motors import Motors
from lib.enums import Orientation
from lib.gamepad import Gamepad
from lib.pid_ctrl import PIDController
from lib.ioe_pot import Potentiometer
from lib.rotary_ctrl import RotaryControl

# ..............................................................................
def main():

    _level = Level.INFO
    _log = Logger('main', _level)
    _loader = ConfigLoader(_level)
    _config = _loader.configure('config.yaml')

    _rot_ctrl = None

    try:

        # motor configuration: starboard, port or both?
        _orientation = Orientation.BOTH
        USE_ROTARY_ENCODER = True
        ROTATE = True
        DRY_RUN = False

        # .........................................
        _motors = Motors(_config, None, Level.INFO)
        _pot = Potentiometer(_config, Level.WARN)
        _pot.set_output_limits(0.0, 127.0) 

        _limit  = 90.0
#       _min    = -127
        _stbd_velocity  = 0.0
        _port_velocity  = 0.0
        _unscaled_value = 0.0
        _scaled_value   = 0.0
        _value          = 0.0
        _rotate = -1.0 if ROTATE else 1.0

        # rotary controller
        _min    = 90
        _max    = 0
        _step   = 5
        _rot_ctrl = RotaryControl(_config, _min, _max, _step, Level.INFO)

        # configure motors/PID controllers
        if _orientation == Orientation.BOTH or _orientation == Orientation.PORT:
            _port_motor = _motors.get_motor(Orientation.PORT)
            _port_pid = PIDController(_config, _port_motor, level=Level.INFO)
            _port_pid.set_max_velocity(_limit)
            _port_pid.enable()
        if _orientation == Orientation.BOTH or _orientation == Orientation.STBD:
            _stbd_motor = _motors.get_motor(Orientation.STBD)
            _stbd_pid = PIDController(_config, _stbd_motor, level=Level.INFO)
            _stbd_pid.set_max_velocity(_limit)
            _stbd_pid.enable()

#       sys.exit(0)

        try:
            while True:
                if USE_ROTARY_ENCODER:
                    _value = _rot_ctrl.read()
                    _log.info(Fore.BLUE + Style.BRIGHT + 'rotary value: {:<5.2f}'.format(_value))
                else:
                    _unscaled_value = _pot.get_value()
                    _pot.set_rgb(_unscaled_value)
                    _scaled_value = _pot.get_scaled_value()
                    _value = 127.0 - _scaled_value
                    _log.info(Fore.CYAN + Style.BRIGHT + 'read value: {:<5.2f};\t'.format(_value))
                    # pre-process value:
                    if _value > 120.0:
                        _value = _limit
                    elif _value < -120.0:
                        _value = -1.0 * _limit
                if _value > -2.0 and _value < 2.0: # hysteresis?
                    _value = 0.0

                if not DRY_RUN:
                    if _orientation == Orientation.BOTH or _orientation == Orientation.PORT:
                        _port_pid.velocity = _rotate * _value #* 100.0
                        _port_velocity = _port_pid.velocity
                    if _orientation == Orientation.BOTH or _orientation == Orientation.STBD:
                        _stbd_pid.velocity = _value #* 100.0
                        _stbd_velocity = _stbd_pid.velocity

                _log.info(Fore.MAGENTA + 'set point: {:<5.2f} (unscaled/scaled: {:<7.4f}/{:<5.2f});'.format(_value, _unscaled_value, _scaled_value) \
                        + Fore.YELLOW + ' velocity: {:5.2f} / {:5.2f}'.format(_port_velocity, _stbd_velocity))
                time.sleep(0.1)

            _log.info(Fore.YELLOW + 'end of cruising.')

        except KeyboardInterrupt:
            _log.info(Fore.CYAN + Style.BRIGHT + 'Ctrl-C caught: closing...')
        finally:
            if _orientation == Orientation.BOTH or _orientation == Orientation.PORT:
                _port_pid.disable()
            if _orientation == Orientation.BOTH or _orientation == Orientation.STBD:
                _stbd_pid.disable()
            _motors.brake()
            if _rot_ctrl:
                _log.info('resetting rotary encoder...')
                _rot_ctrl.reset()
            time.sleep(1.0)
            _log.info('complete.')

    except Exception as e:
        _log.info(Fore.RED + Style.BRIGHT + 'error in test: {}'.format(e, traceback.format_exc()))
    finally:
        _log.info(Fore.YELLOW + Style.BRIGHT + 'finally.')

if __name__== "__main__":
    main()

#EOF
