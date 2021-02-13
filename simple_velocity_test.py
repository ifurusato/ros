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

from lib.button import Button

ROTATE                       = False # move forward or rotate in place?
_rotate = -1.0 if ROTATE else 1.0
# motor configuration: starboard, port or both?
ORIENTATION = Orientation.STBD       # STBD, PORT or BOTH?

_level = Level.INFO
_log = Logger('main', _level)

# ..............................................................................
def rotate_in_place(_rotary_ctrl, _port_pid, _stbd_pid):
    global test_enabled
    _log.info(Fore.BLUE + Style.BRIGHT + 'rotate in place...')
    _min_value     =  0.0
    _max_value     = 30.0
    _port_setpoint = 0.0
    _stbd_setpoint = 0.0

    # accelerate .......................
    _log.info(Fore.MAGENTA + 'accelerating to set point: {:<5.2f}...'.format(_max_value))
    for _setpoint in numpy.arange(_min_value, _max_value, 1.0):
        if ORIENTATION == Orientation.BOTH or ORIENTATION == Orientation.PORT:
            _port_pid.setpoint = _rotate * _setpoint 
            _port_setpoint = _port_pid.setpoint
        _stbd_pid.setpoint = _setpoint
        _stbd_setpoint = _stbd_pid.setpoint
        _log.info(Fore.MAGENTA + 'setpoint: {:<5.2f};'.format(_setpoint) \
                + Fore.RED   + ' port: {:5.2f} / {:5.2f};'.format(_port_setpoint, _port_pid.velocity) \
                + Fore.GREEN + ' stbd: {:5.2f} / {:5.2f};'.format(_stbd_setpoint, _stbd_pid.velocity))
        time.sleep(0.2)

    # cruise ...........................
    _log.info(Fore.MAGENTA + 'cruising...')
    while test_enabled:
        time.sleep(0.1)
        _log.info('waiting for button B...')
    time.sleep(3.0)

    # decelerate .......................
    _log.info(Fore.MAGENTA + 'decelerating to zero...')
    for _setpoint in numpy.arange(_max_value, 0.0, -1.0):
        if ORIENTATION == Orientation.BOTH or ORIENTATION == Orientation.PORT:
            _port_pid.setpoint = _rotate * _setpoint 
            _port_setpoint = _port_pid.setpoint
        _stbd_pid.setpoint = _setpoint
        _stbd_setpoint = _stbd_pid.setpoint
        _log.info(Fore.MAGENTA + 'setpoint: {:<5.2f};'.format(_setpoint) \
                + Fore.RED   + ' port: {:5.2f} / {:5.2f};'.format(_port_setpoint, _port_pid.velocity) \
                + Fore.GREEN + ' stbd: {:5.2f} / {:5.2f};'.format(_stbd_setpoint, _stbd_pid.velocity))
        time.sleep(0.1)

    _log.info(Fore.MAGENTA + 'end of test.')
    time.sleep(1.0)

# ..............................................................................
def callback_method_A(value):
    global test_triggered
    test_triggered = not test_triggered
    _log.info('callback method fired;\t' + Fore.YELLOW + 'action A: {}'.format(test_triggered))

# ..............................................................................
def callback_method_B(value):
    global test_enabled
    test_enabled = not test_enabled
    _log.info('callback method fired;\t' + Fore.YELLOW + 'action B: {}'.format(test_enabled))

# ..............................................................................
def main():
    global test_triggered, test_enabled
    # initial states
    test_triggered = False
    test_enabled   = True

    _loader = ConfigLoader(_level)
    _config = _loader.configure('config.yaml')

    _pin_A = 12
    _button_24 = Button(_pin_A, callback_method_A, Level.INFO)
    _log.info(Style.BRIGHT + 'press button A (connected to pin {:d}) to toggle or initiate action.'.format(_pin_A))

    _pin_B = 24
    _button_24 = Button(_pin_B, callback_method_B, Level.INFO)
    _log.info(Style.BRIGHT + 'press button B connected to pin {:d}) to exit.'.format(_pin_B))

    try:

        # .........................................
        _motors = Motors(_config, None, Level.INFO)
        _pot = Potentiometer(_config, Level.WARN)

        _pot_min = 0.0000
        _pot_max = 0.1500
        _pot.set_output_limits(_pot_min, _pot_max)

        _limit  = 90.0
#       _min    = -127
        _stbd_setpoint  = 0.0
        _port_setpoint  = 0.0
        _scaled_value   = 0.0
        _value          = 0.0
        _port_pid       = None
        _stbd_pid       = None

        # rotary controller
        _min    = 90
        _max    = 0
        _step   = 5
        _rotary_ctrl = RotaryControl(_config, _min, _max, _step, Level.INFO)

        # configure motors/PID controllers
        _port_motor = _motors.get_motor(Orientation.PORT)
        _port_pid = PIDController(_config, _port_motor, level=Level.INFO)
        _port_pid.set_limit(_limit)
        if ORIENTATION == Orientation.BOTH or ORIENTATION == Orientation.PORT:
            _port_pid.enable()
        if ORIENTATION == Orientation.BOTH or ORIENTATION == Orientation.STBD:
            _stbd_motor = _motors.get_motor(Orientation.STBD)
            _stbd_pid = PIDController(_config, _stbd_motor, level=Level.INFO)
            _stbd_pid.set_limit(_limit)
            _stbd_pid.enable()

#       sys.exit(0)

        _fixed_value       = 15.0  # fixed setpoint value
        DRY_RUN            = False
        USE_POTENTIOMETER  = False
        USE_ROTARY_ENCODER = False
        ANYTHING_ELSE      = False

        try:
            while test_enabled:
                if test_triggered:
                    _log.info(Fore.BLUE + Style.BRIGHT + 'action A.')
                    test_triggered = False # trigger once
                    rotate_in_place(_rotary_ctrl, _port_pid, _stbd_pid)
                    test_enabled = False # quit after action
                    time.sleep(1.0)
                    # and we now return to our regularly scheduled broadcast...
                _kp = _pot.get_scaled_value(True)
                _stbd_pid._pid.kp = _kp
                _log.info(Fore.YELLOW + 'waiting for button A...;' + Style.BRIGHT + ' kp: {:8.5f}'.format(_stbd_pid._pid.kp))
                time.sleep(1.0)

            _log.info(Fore.YELLOW + 'end of test.')

        except KeyboardInterrupt:
            _log.info(Fore.CYAN + Style.BRIGHT + 'Ctrl-C caught: closing...')
        finally:
            if ORIENTATION == Orientation.BOTH or ORIENTATION == Orientation.PORT:
                _port_pid.disable()
            if ORIENTATION == Orientation.BOTH or ORIENTATION == Orientation.STBD:
                _stbd_pid.disable()
            _motors.brake()
            if _rotary_ctrl:
                _log.info('resetting rotary encoder...')
                _rotary_ctrl.reset()
            time.sleep(1.0)
            _log.info('complete.')

    except Exception as e:
        _log.info(Fore.RED + Style.BRIGHT + 'error in test: {}'.format(e, traceback.format_exc()))
    finally:
        _log.info(Fore.YELLOW + Style.BRIGHT + 'finally.')

if __name__== "__main__":
    main()

#EOF
