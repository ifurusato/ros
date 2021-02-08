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
# Tests the port and starboard motors for encoder ticks.
#

import pytest
import sys, numpy, time, traceback
from datetime import datetime as dt
from colorama import init, Fore, Style
init()
from lib.rate import Rate
from lib.message_bus import MessageBus
from lib.message_factory import MessageFactory
from lib.clock import Clock, Tick, Tock
from lib.enums import Orientation
from lib.logger import Logger, Level
from lib.config_loader import ConfigLoader
from lib.motor_configurer import MotorConfigurer
from lib.rotary_ctrl import RotaryControl
from lib.button import Button

# settings ................
USE_ROTARY_CONTROL = True # otherwise just set at 30.0
PORT_REVERSE = False      # False runs the port wheel counter-clockwise
STBD_REVERSE = False      # True runs the starboard wheel clockwise
ENABLE_PORT = True        # enable port motor
ENABLE_STBD = True        # enable starboard motor
DECELERATE  = True        # if True decelerate at end, otherwise just stop suddenly
INFINITE    = True        # if True run til Ctrl-C otherwise go 1 meter

_stbd_rotate = -1.0 if STBD_REVERSE else 1.0
_port_rotate = -1.0 if PORT_REVERSE else 1.0

# ..............................................................................
@pytest.mark.unit
def test_motors():
    global _port_motor, _stbd_motor

    _log = Logger('test', Level.INFO)

    # read YAML configuration
    _loader = ConfigLoader(Level.INFO)
    filename = 'config.yaml'
    _config = _loader.configure(filename)

    _log.info('creating message factory...')
    _message_factory = MessageFactory(Level.INFO)
    _log.info('creating message bus...')
    _message_bus = MessageBus(Level.INFO)
    _log.info('creating clock...')
    _clock = Clock(_config, _message_bus, _message_factory, Level.WARN)

    _motor_configurer = MotorConfigurer(_config, _clock, Level.INFO)
    _motors = _motor_configurer.get_motors()
    _motors.enable()

#   _pin_A = 12
#   _button_24 = Button(_pin_A, reset_step_count, Level.INFO)
#   _log.info(Style.BRIGHT + 'press button A (connected to pin {:d}) to toggle or initiate action.'.format(_pin_A))

    _min  = 0
    _max  = 100
    _step = 5
    _rot_ctrl = RotaryControl(_config, _min, _max, _step, Level.WARN)

    _log.info('starting motors...')

    _port_motor = _motors.get_motor(Orientation.PORT)
    _stbd_motor = _motors.get_motor(Orientation.STBD)
    if ENABLE_PORT:
        _port_motor.enable()
    if ENABLE_STBD:
        _stbd_motor.enable()

    _rate = Rate(10)
    _step_limit = 2312

    _start_time = dt.now()

    try:

#       while True:
        while INFINITE or ( _port_motor.steps < _step_limit and _stbd_motor.steps < _step_limit ):

            if USE_ROTARY_CONTROL:
                _read_value = _rot_ctrl.read() 
            else:
                _read_value = 30.0

            _power = _read_value / 100.0
#           _log.info(Fore.YELLOW + 'power: {:5.2f};'.format(_power) + Fore.BLACK + ' read value: {:5.2f}'.format(_read_value))
            if ENABLE_STBD:
                _stbd_motor.set_motor_power(_stbd_rotate * _power)
            if ENABLE_PORT:
                _port_motor.set_motor_power(_port_rotate * _power)
#           _log.info(Fore.RED   + 'power {:5.2f}/{:5.2f}; {:>4d} steps; \t'.format(_stbd_motor.get_current_power_level(), _power, _port_motor.steps) \
#                   + Fore.GREEN + 'power {:5.2f}/{:5.2f}; {:>4d} steps.'.format(_port_motor.get_current_power_level(), _power, _stbd_motor.steps))
            _rate.wait()
    
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
    print(Fore.YELLOW + 'reset step count from:\t' + Fore.RED + 'port: {:>4d} steps;\t'.format(_port_motor.steps) + Fore.GREEN + ' stbd: {:>4d} steps.'.format(_stbd_motor.steps) + Style.RESET_ALL)
    _port_motor.reset_steps()
    _stbd_motor.reset_steps()

# ..............................................................................
def main():

    try:
        test_motors()
    except Exception as e:
        print(Fore.RED + 'error in motor test: {}'.format(e) + Style.RESET_ALL)
        traceback.print_exc(file=sys.stdout)
    finally:
        pass


if __name__== "__main__":
    main()

#EOF
