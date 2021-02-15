#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# Copyright 2020 by Murray Altheim. All rights reserved. This file is part of
# the Robot Operating System project and is released under the "Apache Licence, 
# Version 2.0". Please see the LICENSE file included as part of this package.
#
# author:   Murray Altheim
# created:  2020-10-05
# modified: 2021-02-07
#
# Tests the port and starboard motors for encoder ticks. This includes a quick
# and dirty velocity to power converter to convert a rotary encoder output to
# motor power.
#

import pytest
import sys, numpy, time, traceback
from datetime import datetime as dt
from colorama import init, Fore, Style
init()
from lib.rate import Rate
from lib.message_bus import MessageBus
from lib.message_factory import MessageFactory
from lib.clock import Clock
from lib.enums import Orientation
from lib.logger import Logger, Level
from lib.config_loader import ConfigLoader
from lib.motor import Motor
from lib.motor_configurer import MotorConfigurer
from lib.rotary_ctrl import RotaryControl
from lib.button import Button
from lib.moth import Moth
from lib.rgbmatrix import RgbMatrix, Color, DisplayType

# settings ................
ENABLE_MOTH = False       # enable moth behaviour
USE_ROTARY_CONTROL = True # otherwise just set at 30.0
PORT_REVERSE = False      # False runs the port wheel counter-clockwise
STBD_REVERSE = False      # True runs the starboard wheel clockwise

ENABLE_PORT = True        # enable port motor
ENABLE_STBD = True        # enable starboard motor
DECELERATE  = True        # if True decelerate at end, otherwise just stop suddenly
INFINITE    = True        # if True run til Ctrl-C otherwise go 1 meter

if ENABLE_MOTH: # then assume some other things
    INFINITE    = False
    ENABLE_PORT = True
    ENABLE_STBD = True 
    USE_ROTARY_CONTROL = True

_stbd_rotate = -1.0 if STBD_REVERSE else 1.0
_port_rotate = -1.0 if PORT_REVERSE else 1.0

_log = Logger('test', Level.INFO)

# ..............................................................................
@pytest.mark.unit
def test_velocity_to_power_conversion():
    # velocity to power conversion test:
    for v in numpy.arange(0.0, 60.0, 2.0):
        p = Motor.velocity_to_power(v)
        _log.info('velocity: {:5.2f};'.format(v) + Fore.YELLOW + ' power: {:5.2f};'.format(p))

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
@pytest.mark.unit
def test_motors():
    global _port_motor, _stbd_motor, action_A, action_B

    # read YAML configuration
    _loader = ConfigLoader(Level.INFO)
    filename = 'config.yaml'
    _config = _loader.configure(filename)

    _log.info('creating message factory...')
    _message_factory = MessageFactory(Level.INFO)
    _log.info('creating message bus...')
    _message_bus = MessageBus(Level.WARN)
    _log.info('creating clock...')
    _clock = Clock(_config, _message_bus, _message_factory, Level.WARN)

    _motor_configurer = MotorConfigurer(_config, _clock, Level.INFO)
    _motors = _motor_configurer.get_motors()
    _motors.enable()

    if ENABLE_MOTH:
        _rgbmatrix = RgbMatrix(Level.WARN)
#       _rgbmatrix.set_display_type(DisplayType.SOLID)
        _moth = Moth(_config, None, Level.WARN)

    _pin_A = 12
    _button_12 = Button(_pin_A, callback_method_A, Level.INFO)
    _log.info(Style.BRIGHT + 'press button A (connected to pin {:d}) to toggle or initiate action.'.format(_pin_A))

    _pin_B = 24
    _button_24 = Button(_pin_B, callback_method_B, Level.INFO)
    _log.info(Style.BRIGHT + 'press button B connected to pin {:d}) to exit.'.format(_pin_B))

    _log.info('starting motors...')
    _port_motor = _motors.get_motor(Orientation.PORT)
    _stbd_motor = _motors.get_motor(Orientation.STBD)
    if ENABLE_PORT:
        _port_motor.enable()
    if ENABLE_STBD:
        _stbd_motor.enable()

    _rot_ctrl = RotaryControl(_config, 0, 50, 2, Level.WARN) # min, max, step
    _rate = Rate(5)
    _step_limit = 2312
    _velocity_stbd = 0.0
    _velocity_port = 0.0
    _start_time    = dt.now()
    _moth_port     = 1.0
    _moth_stbd     = 1.0
    _moth_offset   = 0.6
    _moth_bias     = [ 0.0, 0.0 ]
    _moth_fudge    = 0.7

    try:

        action_A = False
        action_B = True

        while action_B or INFINITE or ( _port_motor.steps < _step_limit and _stbd_motor.steps < _step_limit ):
            if action_A:
                action_A = False # trigger once
                while action_B:
                    if USE_ROTARY_CONTROL:
                        _target_velocity = _rot_ctrl.read() 
                    else:
                        _target_velocity = 30.0
        #           _power = _target_velocity / 100.0
                    _power = Motor.velocity_to_power(_target_velocity)
                    if ENABLE_MOTH:
                        _moth_bias = _moth.get_bias()
#                       _log.info(Fore.WHITE + Style.BRIGHT + 'port: {:5.2f}; stbd: {:5.2f}'.format(_moth_port, _moth_stbd))
#                       _rgbmatrix.show_hue(_moth_hue, Orientation.BOTH)
                        _orientation = _moth.get_orientation()
                        if _orientation is Orientation.PORT:
                            _moth_port = _moth_bias[0] * _moth_fudge
                            _moth_stbd = 1.0
                            _rgbmatrix.show_color(Color.BLACK, Orientation.STBD)
                            _rgbmatrix.show_color(Color.RED, Orientation.PORT)
                        elif _orientation is Orientation.STBD:
                            _moth_port = 1.0
                            _moth_stbd = _moth_bias[1] * _moth_fudge 
                            _rgbmatrix.show_color(Color.BLACK, Orientation.PORT)
                            _rgbmatrix.show_color(Color.GREEN, Orientation.STBD)
                        else:
                            _moth_port = 1.0
                            _moth_stbd = 1.0
                            _rgbmatrix.show_color(Color.BLACK, Orientation.PORT)
                            _rgbmatrix.show_color(Color.BLACK, Orientation.STBD)
                    if ENABLE_STBD:
                        _stbd_motor.set_motor_power(_stbd_rotate * _power * _moth_stbd)
                        _velocity_stbd = _stbd_motor.velocity
                    if ENABLE_PORT:
                        _port_motor.set_motor_power(_port_rotate * _power * _moth_port)
                        _velocity_port = _port_motor.velocity
                    _log.info(Fore.YELLOW + 'power: {:5.2f}; bias: '.format(_power) \
                            + Fore.RED + ' {:5.2f} '.format(_moth_bias[0]) + Fore.GREEN + '{:5.2f};'.format(_moth_bias[1]) \
                            + Fore.BLACK + ' target velocity: {:5.2f};'.format(_target_velocity) \
                            + Fore.CYAN + ' velocity: ' \
                            + Fore.RED   + ' {:5.2f} '.format(_velocity_port) + Fore.GREEN + ' {:5.2f}'.format(_velocity_stbd))
                    
        #           _log.info(Fore.RED   + 'power {:5.2f}/{:5.2f}; {:>4d} steps; \t'.format(_stbd_motor.get_current_power_level(), _power, _port_motor.steps) \
        #                   + Fore.GREEN + 'power {:5.2f}/{:5.2f}; {:>4d} steps.'.format(_port_motor.get_current_power_level(), _power, _stbd_motor.steps))
                    _rate.wait()
                action_B = True # reentry into B loop, waiting for A
            _log.info('waiting for A button press...')
            time.sleep(1.0)
            # end wait loop ....................................................

        if ENABLE_PORT:
            _log.info('port motor: {:d} steps.'.format(_port_motor.steps))
        if ENABLE_STBD:
            _log.info('stbd motor: {:d} steps.'.format(_stbd_motor.steps))

    except KeyboardInterrupt:
        _log.info('Ctrl-C caught; exiting...')
    except Exception as e:
        _log.error('error: {}'.format(e))
    finally:
        close_motors(_log)
    _elapsed_ms = round(( dt.now() - _start_time ).total_seconds() * 1000.0)
    _log.info(Fore.YELLOW + 'complete: elapsed: {:d}ms'.format(_elapsed_ms))

# ..............................................................................
def close_motors(_log):
    global _port_motor, _stbd_motor
    '''
    Decelerate to stop. Failing that, just stop.
    '''
    _log.info('closing motors...')
    try:
        if DECELERATE:
            if _stbd_motor.get_current_power_level() > 0.0 or _port_motor.get_current_power_level() > 0.0:
                _init_power = _stbd_motor.get_current_power_level()
                for _power in numpy.arange(_init_power, 0.0, -0.01):
                    _log.info('setting motor power: {:5.2f}'.format(_power))
                    if ENABLE_STBD:
                        _stbd_motor.set_motor_power(_stbd_rotate * _power)
                    if ENABLE_PORT:
                        _port_motor.set_motor_power(_port_rotate * _power)
                    time.sleep(0.05)
            else:
                _log.warning('motor power already appears at zero.')
            time.sleep(0.5)
        # else just stop suddenly
    except Exception as e:
        _log.error('error during motor close: {}'.format(e))
    finally:
        if ENABLE_PORT:
            if _port_motor != None:
                _port_motor.set_motor_power(0.0)
        if ENABLE_STBD:
            if _stbd_motor != None:
                _stbd_motor.set_motor_power(0.0)

# ..............................................................................
def reset_step_count(value):
    global _port_motor, _stbd_motor
    print(Fore.YELLOW + 'reset step count from:\t' \
            + Fore.RED + 'port: {:>4d} steps;\t'.format(_port_motor.steps) \
            + Fore.GREEN + ' stbd: {:>4d} steps.'.format(_stbd_motor.steps) + Style.RESET_ALL)
    _port_motor.reset_steps()
    _stbd_motor.reset_steps()

# ..............................................................................
def main():

    try:
#       test_velocity_to_power_conversion()
        test_motors()
    except Exception as e:
        print(Fore.RED + 'error in motor test: {}'.format(e) + Style.RESET_ALL)
        traceback.print_exc(file=sys.stdout)
    finally:
        pass


if __name__== "__main__":
    main()

#EOF
