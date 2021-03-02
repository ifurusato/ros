#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# Copyright 2020-2021 by Murray Altheim. All rights reserved. This file is part
# of the Robot Operating System project, released under the MIT License. Please
# see the LICENSE file included as part of this package.
#
# A quick test of the simple_pid library.

import sys, time, traceback
import numpy
from colorama import init, Fore, Style
init()

from lib.logger import Logger, Level
from lib.config_loader import ConfigLoader

from lib.motors import Motors
from lib.enums import Orientation
from lib.rotary_ctrl import RotaryControl
from lib.ioe_pot import Potentiometer
#from lib.status import Status
#from lib.pot import Potentiometer 
from lib.pid_ctrl import PIDController

# ..............................................................................
def main():

    _level = Level.INFO
    _log = Logger('main', _level)
    _loader = ConfigLoader(_level)
    _config = _loader.configure('config.yaml')
    _rot_min  = 0
    _rot_max  = 100
    _rot_step = 5
    _rot_ctrl = RotaryControl(_config, _rot_min, _rot_max, _rot_step, Level.WARN)

    _pot_min  = 0.0
    _pot_max  = 0.00030
    _pot = Potentiometer(_config, Level.INFO)
    _pot.set_output_limits(_pot_min, _pot_max)

    try:
        _motors = Motors(_config, None, _level)
#       _port_motor = _motors.get_motor(Orientation.PORT)
#       _port_pid = PIDController(_config, _port_motor, level=Level.DEBUG)

        _stbd_motor = _motors.get_motor(Orientation.STBD)
        _stbd_pid = PIDController(_config, _stbd_motor, level=Level.DEBUG)

#       sys.exit(0)

        _max_velocity = 30.0
#       _port_pid.enable()
        _stbd_pid.enable()

        try:

            _log.info(Fore.YELLOW + 'accelerating...')

            _read_value = _rot_ctrl.read() 
            _velocity = _read_value / 100.0
            _log.info(Fore.YELLOW + 'value: {}'.format(_read_value))
            _stbd_pid.setpoint = 10.0

#           for _velocity in numpy.arange(0.0, _max_velocity, 0.3):
#               _log.info(Fore.YELLOW + '_velocity={:>5.2f}.'.format(_velocity))
#               _stbd_pid.setpoint = _velocity
#               _log.info(Fore.GREEN + 'STBD setpoint={:>5.2f}.'.format(_stbd_pid.setpoint))
#               _port_pid.setpoint = _velocity
#               _log.info(Fore.RED   + 'PORT setpoint={:>5.2f}.'.format(_port_pid.setpoint))

#               time.sleep(1.0)
                # ..........................................

            _log.info(Fore.YELLOW + 'cruising...')
            time.sleep(10.0)
            _log.info(Fore.YELLOW + 'end of cruising.')

#           _log.info(Fore.YELLOW + 'decelerating...')
#           for _velocity in numpy.arange(_max_velocity, 0.0, -0.25):
#               _log.info(Fore.YELLOW + '_velocity={:>5.2f}.'.format(_velocity))
#               _port_pid.setpoint = _velocity
#               _stbd_pid.setpoint = _velocity
#               _log.info(Fore.GREEN + 'STBD setpoint={:>5.2f}.'.format(_stbd_pid.setpoint))
#               _log.info(Fore.RED   + 'PORT setpoint={:>5.2f}.'.format(_port_pid.setpoint))
#               time.sleep(1.0)

#           _log.info(Fore.YELLOW + 'stopped...')
            _stbd_pid.setpoint = 0.0
            time.sleep(3.0)
            _log.info(Fore.YELLOW + 'end of test.')

        except KeyboardInterrupt:
            _log.info(Fore.CYAN + Style.BRIGHT + 'PID test complete.')
        finally:
#           _port_pid.disable()
            _stbd_pid.disable()
            _motors.brake()

    except Exception as e:
        _log.info(Fore.RED + Style.BRIGHT + 'error in PID controller: {}'.format(e))
        traceback.print_exc(file=sys.stdout)
    finally:
        _log.info(Fore.YELLOW + Style.BRIGHT + 'C. finally.')


if __name__== "__main__":
    main()

#EOF
