#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# created:  2020-10-05
# modified: 2020-10-05
#
# Extends the motors_test to capture the velocity of the
# port and starboard motors based on encoder ticks.
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
from lib.pid_ctrl import PIDController
from lib.ioe_pot import Potentiometer
from lib.rotary_ctrl import RotaryControl

ORIENTATION = Orientation.STBD       # STBD, PORT or BOTH?
POT_CONTROL = False                  # otherwise use rotary encoder

# ..............................................................................
def close_motors(_log, port_motor, stbd_motor):
    '''
    Decelerate to stop.
    '''
    _log.info('closing motors...')
    if stbd_motor.get_current_power_level() > 0.0 or port_motor.get_current_power_level() > 0.0:
        _init_power = stbd_motor.get_current_power_level()
        for _power in numpy.arange(_init_power, 0.0, -0.01):
            _log.info('setting motor power: {:5.2f}'.format(_power))
            stbd_motor.set_motor_power(_power)
            port_motor.set_motor_power(-1.0 * _power)
            time.sleep(0.05)
    else:
        _log.warning('motor power already appears at zero.')
    time.sleep(0.1)
    port_motor.set_motor_power(0.0)
    stbd_motor.set_motor_power(0.0)

# ..............................................................................
@pytest.mark.unit
def test_motors():

    _log = Logger('test', Level.INFO)
    # read YAML configuration
    _loader = ConfigLoader(Level.INFO)
    filename = 'config.yaml'
    _config = _loader.configure(filename)

    # rotary controller
    _min    = 0
    _max    = 50
    _step   = 5
    _rotary_ctrl = RotaryControl(_config, _min, _max, _step, Level.WARN)

    _motor_configurer = MotorConfigurer(_config, Level.INFO)
    _motors = _motor_configurer.configure()
    _motors.enable()

    _log.info('starting motors...')

    _port_motor = _motors.get_motor(Orientation.PORT)
    _port_pid = PIDController(_config, _port_motor, level=Level.INFO)
    if ORIENTATION == Orientation.BOTH or ORIENTATION == Orientation.PORT:
        _port_motor.enable()
        _port_pid.enable()

    _stbd_motor = _motors.get_motor(Orientation.STBD)
    _stbd_pid = PIDController(_config, _stbd_motor, level=Level.INFO)
    _stbd_motor.enable()
    _stbd_pid.enable()

    _power = 0.0
    _pot = Potentiometer(_config, Level.WARN)
    if POT_CONTROL:
        _pot_limit = 1.0
    else:
        _pot_limit = 0.0
    _pot.set_output_limits(0.0, _pot_limit) 


    try:

        _rate = Rate(10)
        i = 0
#       for i in range(7):
        while True:

            _rot_value = _rotary_ctrl.read()
#           _unscaled_value = _pot.get_value()
#           _pot.set_rgb(_unscaled_value)
            _scaled_value = _pot.get_scaled_value(True)
            _log.info('rotary : {:<5.2f};'.format(_rot_value) + ' pot: {:<5.2f}'.format(_scaled_value))

            if POT_CONTROL:
                _power = _scaled_value
#               _power = i * 0.1 
                _log.info(Fore.YELLOW + 'set motor power: {:5.2f} (original: {:d});'.format(_power, i))
                if ORIENTATION == Orientation.BOTH or ORIENTATION == Orientation.PORT:
                    _port_motor.set_motor_power(-1.0 * _power)
                _stbd_motor.set_motor_power(_power)
                _log.info('[{:d}]\t'.format(i) \
                        + Fore.RED   + 'power {:5.2f}/{:5.2f}; {:>4d} steps; setpoint: {:5.2f}; velocity: {:5.2f};\t'.format(\
                                _stbd_motor.get_current_power_level(), _power, _port_pid.steps, _port_pid.setpoint, _port_pid.velocity) \
                        + Fore.GREEN + 'power {:5.2f}/{:5.2f}; {:>4d} steps; setpoint: {:5.2f}; velocity: {:5.2f}'.format(\
                                _port_motor.get_current_power_level(), _power, _stbd_pid.steps, _stbd_pid.setpoint, _stbd_pid.velocity))
            else:
                if ORIENTATION == Orientation.BOTH or ORIENTATION == Orientation.PORT:
                    _port_pid.setpoint = _rot_value
                _stbd_pid.setpoint = _rot_value
#               _log.info(Fore.RED + 'STBD value: {:5.2f} setpoint: {:5.2f}'.format(_scaled_value, _stbd_pid.setpoint) + Style.RESET_ALL)
                _log.info('[{:d}]\t'.format(i) \
                        + Fore.RED   + 'motor power {:5.2f}; {:>4d} steps; setpoint: {:5.2f}; velocity: {:5.2f};\t'.format(\
                                _stbd_motor.get_current_power_level(), _port_pid.steps, _port_pid.setpoint, _port_pid.velocity) \
                        + Fore.GREEN + 'motor power {:5.2f}; {:>4d} steps; setpoint: {:5.2f}; velocity: {:5.2f}'.format(\
                                _port_motor.get_current_power_level(), _stbd_pid.steps, _stbd_pid.setpoint, _stbd_pid.velocity))

#           if i > 2 and ( _port_motor.steps == 0 or _stbd_motor.steps == 0 ):
#               raise Exception('motors are not turning.')
#           time.sleep(1.0)
#           time.sleep(1.0)
            _rate.wait()
    
        # tests...
        if ORIENTATION == Orientation.BOTH or ORIENTATION == Orientation.PORT:
            _log.info('port motor: {:d} steps.'.format(_port_pid.steps))
#       assert _port_motor.steps > 0
        _log.info('stbd motor: {:d} steps.'.format(_stbd_pid.steps))
#       assert _stbd_motor.steps > 0

    except Exception as e:
        _log.error('error: {}'.format(e))
    finally:
        close_motors(_log, _port_motor, _stbd_motor)

    _log.info(Fore.YELLOW + 'complete.')

# ..............................................................................
def main():

    try:
        test_motors()
    except KeyboardInterrupt:
        print(Fore.CYAN + 'Ctrl-C caught; exiting...' + Style.RESET_ALL)
    except Exception as e:
        print(Fore.RED + 'error in motor test: {}'.format(e) + Style.RESET_ALL)
        traceback.print_exc(file=sys.stdout)
    finally:
        pass


if __name__== "__main__":
    main()

#EOF
