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

USE_ROTARY_ENCODER           = False
USE_POTENTIOMETER            = False
DRY_RUN                      = False
ROTATE                       = False # move forward or rotate in place?
# motor configuration: starboard, port or both?
ORIENTATION = Orientation.STBD       # STBD, PORT or BOTH?
ACCELERATE_COUNTER_CLOCKWISE = True
ACCELERATE_CLOCKWISE         = False
_fixed_value                 = 15.0  # fixed setpoint value

_level = Level.INFO
_log = Logger('main', _level)

# ..............................................................................
def rotate_in_place(_rotary_ctrl, _port_pid, _stbd_pid):
    global action_B
    _log.info(Fore.BLUE + Style.BRIGHT + 'rotate in place...')
    _rotate = -1.0 if ROTATE else 1.0
    _min_value =  0.0
    _max_value = 50.0
    _port_setpoint = 0.0
    _stbd_setpoint = 0.0

    if ACCELERATE_COUNTER_CLOCKWISE:
        _log.info(Fore.MAGENTA + Style.BRIGHT + 'ACCELERATE_COUNTER_CLOCKWISE ------------------------------------------ ')
        # accelerate
        _log.info(Fore.MAGENTA + 'accelerating to set point: {:<5.2f}...'.format(_max_value))
        for _value in numpy.arange(_min_value, _max_value, 1.0):
            if ORIENTATION == Orientation.BOTH or ORIENTATION == Orientation.PORT:
                _port_pid.setpoint = _rotate * _value 
                _port_setpoint = _port_pid.setpoint
            _stbd_pid.setpoint = _value
            _stbd_setpoint = _stbd_pid.setpoint
            _log.info(Fore.MAGENTA + 'set point: {:<5.2f};'.format(_value) \
                + Fore.YELLOW + ' setpoint: {:5.2f} / {:5.2f};'.format(_port_setpoint, _stbd_setpoint))
            time.sleep(0.1)
        # cruise
        if not action_B:
            _log.info('cancelled.')
            return
        _log.info(Fore.MAGENTA + 'cruising...')
        time.sleep(5.0)
        # decelerate
        _log.info(Fore.MAGENTA + 'decelerating to zero...')
        for _value in numpy.arange(_max_value, 0.0, -1.0):
            if ORIENTATION == Orientation.BOTH or ORIENTATION == Orientation.PORT:
                _port_pid.setpoint = _rotate * _value 
                _port_setpoint = _port_pid.setpoint
            _stbd_pid.setpoint = _value
            _stbd_setpoint = _stbd_pid.setpoint
            _log.info(Fore.MAGENTA + 'set point: {:<5.2f};'.format(_value) \
                + Fore.YELLOW + ' setpoint: {:5.2f} / {:5.2f};'.format(_port_setpoint, _stbd_setpoint))
            time.sleep(0.1)

    if not action_B:
        _log.info('cancelled.')
        return

    # wait a bit ...........................
    _log.info(Fore.MAGENTA + Style.BRIGHT + 'BEGIN PAUSE AT ZERO --------------------------------------------------- ')
    if ORIENTATION == Orientation.BOTH or ORIENTATION == Orientation.PORT:
        _port_pid.reset()
        _port_pid.print_state()
    _stbd_pid.reset()
    _stbd_pid.print_state() 
    time.sleep(5.0)
    _log.info(Fore.MAGENTA + Style.BRIGHT + 'END PAUSE AT ZERO ----------------------------------------------------- ')

    if not action_B:
        _log.info('cancelled.')
        return
    if ACCELERATE_CLOCKWISE:
        _log.info(Fore.MAGENTA + Style.BRIGHT + 'ACCELERATE_CLOCKWISE -------------------------------------------------- ')
        # accelerate
        _log.info(Fore.MAGENTA + 'accelerating to set point: {:<5.2f}...'.format(_max_value))
        for _value in numpy.arange(_min_value, _max_value, 1.0):
            if ORIENTATION == Orientation.BOTH or ORIENTATION == Orientation.PORT:
                _port_pid.setpoint = _value 
                _port_setpoint = _port_pid.setpoint
            _stbd_pid.setpoint = _rotate * _value
            _stbd_setpoint = _stbd_pid.setpoint
            _log.info(Fore.MAGENTA + 'set point: {:<5.2f};'.format(_value) \
                + Fore.YELLOW + ' setpoint: {:5.2f} / {:5.2f};'.format(_port_setpoint, _stbd_setpoint))
            time.sleep(0.1)
        if not action_B:
            _log.info('cancelled.')
            return
        # cruise
        _log.info(Fore.MAGENTA + 'cruising...')
        time.sleep(5.0)
        # decelerate
        _log.info(Fore.MAGENTA + 'decelerating to zero...')
        for _value in numpy.arange(_max_value, 0.0, -1.0):
            if ORIENTATION == Orientation.BOTH or ORIENTATION == Orientation.PORT:
                _port_pid.setpoint = _value 
                _port_setpoint = _port_pid.setpoint
            _stbd_pid.setpoint = _rotate * _value
            _stbd_setpoint = _stbd_pid.setpoint
            _log.info(Fore.MAGENTA + 'set point: {:<5.2f};'.format(_value) \
                + Fore.YELLOW + ' setpoint: {:5.2f} / {:5.2f};'.format(_port_setpoint, _stbd_setpoint))
            time.sleep(0.1)

        # wait a bit ...........................
        if ORIENTATION == Orientation.BOTH or ORIENTATION == Orientation.PORT:
            _port_pid.setpoint = 0.0
            _port_pid.print_state()
        _stbd_pid.setpoint = 0.0
        _stbd_pid.print_state() 

    _log.info(Fore.MAGENTA + 'end of test.')
    time.sleep(5.0)

# ..............................................................................
def callback_method_A(value):
    global action_A
    action_A = not action_A
    _log.info('callback method fired;\t' + Fore.YELLOW + 'action A: {}'.format(action_A))

# ..............................................................................
def callback_method_B(value):
    global action_B
    action_B = not action_B
    _log.info('callback method fired;\t' + Fore.YELLOW + 'action B: {}'.format(action_B))

# ..............................................................................
def main():
    global action_A, action_B
    # initial states
    action_A = False
    action_B = True

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
        _pot.set_output_limits(0.0, 127.0) 

        _limit  = 90.0
#       _min    = -127
        _stbd_setpoint  = 0.0
        _port_setpoint  = 0.0
        _unscaled_value = 0.0
        _scaled_value   = 0.0
        _value          = 0.0
        _rotate = -1.0 if ROTATE else 1.0
        _port_pid       = None
        _stbd_pid       = None

        # rotary controller
        _min    = 90
        _max    = 0
        _step   = 5
        _rotary_ctrl = RotaryControl(_config, _min, _max, _step, Level.INFO)

        # configure motors/PID controllers
        if ORIENTATION == Orientation.BOTH or ORIENTATION == Orientation.PORT:
            _port_motor = _motors.get_motor(Orientation.PORT)
            _port_pid = PIDController(_config, _port_motor, level=Level.INFO)
            _port_pid.set_limit(_limit)
            _port_pid.enable()
        if ORIENTATION == Orientation.BOTH or ORIENTATION == Orientation.STBD:
            _stbd_motor = _motors.get_motor(Orientation.STBD)
            _stbd_pid = PIDController(_config, _stbd_motor, level=Level.INFO)
            _stbd_pid.set_limit(_limit)
            _stbd_pid.enable()

#       sys.exit(0)

        try:
            while action_B:
                if action_A:
                    _log.info(Fore.BLUE + Style.BRIGHT + 'action A.')
                    action_A = False # trigger once
                    rotate_in_place(_rotary_ctrl, _port_pid, _stbd_pid)
                    action_B = False # quit after action
                    time.sleep(1.0)
                    # and we now return to our regularly scheduled broadcast...
                else:
                    if USE_ROTARY_ENCODER:
                        _value = _rotary_ctrl.read()
                        _log.info(Fore.BLUE + Style.BRIGHT + 'rotary value: {:<5.2f}'.format(_value))
                    elif USE_POTENTIOMETER:
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
                    else:
                        _value = _fixed_value

                    if _value > -2.0 and _value < 2.0: # hysteresis?
                        _value = 0.0
    
                    if not DRY_RUN:
                        if ORIENTATION == Orientation.BOTH or ORIENTATION == Orientation.PORT:
                            _port_pid.setpoint = _rotate * _value #* 100.0
                            _port_setpoint = _port_pid.setpoint
                        if ORIENTATION == Orientation.BOTH or ORIENTATION == Orientation.STBD:
                            _stbd_pid.setpoint = _value #* 100.0
                            _stbd_setpoint = _stbd_pid.setpoint
    
                    _log.info(Fore.MAGENTA + 'set point: {:<5.2f} (unscaled/scaled: {:<7.4f}/{:<5.2f});'.format(_value, _unscaled_value, _scaled_value) \
                            + Fore.YELLOW + ' setpoint: {:5.2f} / {:5.2f};'.format(_port_setpoint, _stbd_setpoint) + Fore.WHITE + ' action_B: {}'.format(action_B))
                    time.sleep(0.1)

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
