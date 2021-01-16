#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# created:  2020-10-05
# modified: 2020-10-05
#
# Tests the port and starboard motors for both current draw and encoder ticks.
#

import pytest
import sys, time, traceback
import numpy
from colorama import init, Fore, Style
init()
from lib.enums import Orientation
from lib.logger import Logger, Level
from lib.config_loader import ConfigLoader
from lib.current import CurrentSensor
from lib.motor_configurer import MotorConfigurer

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
            port_motor.set_motor_power(_power)
            time.sleep(0.1)
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

    _cs = CurrentSensor(_config, Level.INFO)

    _motor_configurer = MotorConfigurer(_config, Level.INFO)
    _motors = _motor_configurer.configure()
    _motors.enable()

    _log.info('starting motors...')

    _port_motor = _motors.get_motor(Orientation.PORT)
    _stbd_motor = _motors.get_motor(Orientation.STBD)
    _port_motor.enable()
    _stbd_motor.enable()

    _port_count = 0
    _stbd_count = 0

    try:
        for i in range(8):
            _power = i * 0.1 
#           _log.info(Fore.YELLOW + 'set motor power: {:5.2f};'.format(_power))
            _stbd_motor.set_motor_power(_power)
            _port_motor.set_motor_power(_power)
            time.sleep(1.0)
            _current = _cs.current
            _voltage = _cs.voltage
            _log.info('[{:d}]\t'.format(i) \
                    + Fore.RED   + '{:<7}{:>7.2f}mA, {:4.2f}V @ power {:5.2f}/{:5.2f}; {:>4d} steps; \t'.format( \
                                   'port:', _current[0], _voltage[0], _stbd_motor.get_current_power_level(), _power, _port_motor.steps) \
                    + Fore.GREEN + '{:<7}{:>7.2f}mA, {:4.2f}V @ power {:5.2f}/{:5.2f}; {:>4d} steps.'.format( \
                                   'stbd:', _current[1], _voltage[1], _port_motor.get_current_power_level(), _power, _stbd_motor.steps))
#           _power   = _cs.power
#           _log.info('power:  \t' + Fore.RED + '{:<7}{:>7.2f}mW;\t'.format('port:', _power[0])   + Fore.GREEN + '{:<7}{:>7.2f}mW'.format('stbd:', _power[1]))
            if _current[0] > 0.0:
                _port_count += 1
            if _current[1] > 0.0:
                _stbd_count += 1
            if i > 2 and ( _port_motor.steps == 0 or _stbd_motor.steps == 0 ):
                raise Exception('motors are not turning.')
            time.sleep(1.0)
    
    except Exception as e:
        _log.error('error: {}'.format(e))
    finally:
        close_motors(_log, _port_motor, _stbd_motor)

    # tests...
    assert _port_motor.steps > 0
    assert _stbd_motor.steps > 0
    assert _port_count > 0
    assert _stbd_count > 0
    _log.info(Fore.RED + 'port: {:d};'.format(_port_count) + Fore.GREEN + ' stbd: {:d}; complete.'.format(_stbd_count))
    _log.info(Fore.YELLOW + 'complete.')

# ..............................................................................
def main():

    try:
        test_motors()
    except KeyboardInterrupt:
        print(Fore.RED + 'Ctrl-C caught; exiting...' + Style.RESET_ALL)
    except Exception as e:
        print(Fore.RED + 'error in motor test: {}'.format(e) + Style.RESET_ALL)
        traceback.print_exc(file=sys.stdout)
    finally:
        pass


if __name__== "__main__":
    main()

#EOF
