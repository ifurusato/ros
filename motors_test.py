#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# created:  2020-10-05
# modified: 2020-10-05
#
# Tests the port and starboard motors for encoder ticks.
#

import pytest
import sys, time, traceback
import numpy
from colorama import init, Fore, Style
init()
from lib.rate import Rate
from lib.enums import Orientation
from lib.logger import Logger, Level
from lib.config_loader import ConfigLoader
from lib.motor_configurer import MotorConfigurer
from lib.rotary_ctrl import RotaryControl
from lib.button import Button

STBD_ROTATE = True
PORT_ROTATE = False

_stbd_rotate = -1.0 if STBD_ROTATE else 1.0
_port_rotate = -1.0 if PORT_ROTATE else 1.0

# ..............................................................................
def close_motors(_log):
    global _port_motor, _stbd_motor
    '''
    Decelerate to stop. Failing that, just stop.
    '''
    _log.info('closing motors...')
    try:
        if _stbd_motor.get_current_power_level() > 0.0 or _port_motor.get_current_power_level() > 0.0:
            _init_power = _stbd_motor.get_current_power_level()
            for _power in numpy.arange(_init_power, 0.0, -0.01):
                _log.info('setting motor power: {:5.2f}'.format(_power))
                _stbd_motor.set_motor_power(_stbd_rotate * _power)
                _port_motor.set_motor_power(_port_rotate * _power)
                time.sleep(0.05)
        else:
            _log.warning('motor power already appears at zero.')
        time.sleep(0.5)
    except Exception as e:
        _log.error('error during motor close: {}'.format(e))
    finally:
        if _port_motor != None:
            _port_motor.set_motor_power(0.0)
        if _stbd_motor != None:
            _stbd_motor.set_motor_power(0.0)

# ..............................................................................
@pytest.mark.unit
def test_motors():
    global _port_motor, _stbd_motor

    _log = Logger('test', Level.INFO)
    # read YAML configuration
    _loader = ConfigLoader(Level.INFO)
    filename = 'config.yaml'
    _config = _loader.configure(filename)

    _motor_configurer = MotorConfigurer(_config, Level.INFO)
    _motors = _motor_configurer.configure()
    _motors.enable()

    _pin_A = 12
    _button_24 = Button(_pin_A, reset_step_count, Level.INFO)
    _log.info(Style.BRIGHT + 'press button A (connected to pin {:d}) to toggle or initiate action.'.format(_pin_A))

    _min  = 0
    _max  = 100
    _step = 5
    _rot_ctrl = RotaryControl(_config, _min, _max, _step, Level.INFO)

    _log.info('starting motors...')

    _port_motor = _motors.get_motor(Orientation.PORT)
    _stbd_motor = _motors.get_motor(Orientation.STBD)
    _port_motor.enable()
    _stbd_motor.enable()

    _rate = Rate(10)

    try:
        while True:
            _read_value = _rot_ctrl.read() 
            _power = _read_value / 100.0
            _log.debug(Fore.YELLOW + 'power: {:5.2f};'.format(_power) + Fore.BLACK + ' read value: {:5.2f}'.format(_read_value))
            _stbd_motor.set_motor_power(_stbd_rotate * _power)
            _port_motor.set_motor_power(_port_rotate * _power)
            _log.info(Fore.RED   + 'power {:5.2f}/{:5.2f}; {:>4d} steps; \t'.format(_stbd_motor.get_current_power_level(), _power, _port_motor.steps) \
                    + Fore.GREEN + 'power {:5.2f}/{:5.2f}; {:>4d} steps.'.format(_port_motor.get_current_power_level(), _power, _stbd_motor.steps))
            _rate.wait()
    
        _log.info('port motor: {:d} steps.'.format(_port_motor.steps))
        _log.info('stbd motor: {:d} steps.'.format(_stbd_motor.steps))

    except KeyboardInterrupt:
        _log.info('Ctrl-C caught; exiting...')
    except Exception as e:
        _log.error('error: {}'.format(e))
    finally:
        close_motors(_log, _port_motor, _stbd_motor)

    _log.info(Fore.YELLOW + 'complete.')

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
