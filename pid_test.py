#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# Copyright 2020 by Murray Altheim. All rights reserved. This file is part of
# the Robot OS project and is released under the "Apache Licence, Version 2.0".
# Please see the LICENSE file included as part of this package.
#

# Import library functions we need
import os, sys, signal, time, traceback
from threading import Thread
from fractions import Fraction
from colorama import init, Fore, Style
init()

try:
    import numpy
except ImportError:
    exit("This script requires the numpy module\nInstall with: sudo pip3 install numpy")

from lib.devnull import DevNull
from lib.enums import Rotation, Direction, Speed, Velocity, Orientation
from lib.slew import SlewRate
from lib.logger import Logger, Level
from lib.config_loader import ConfigLoader
from lib.motor import Motor
from lib.motors import Motors
from lib.pid import PID
from lib.filewriter import FileWriter

def quit():
    Motor.cancel()
    sys.stderr = DevNull()
    print('exit.')
    sys.exit(0)

# exception handler ............................................................
def signal_handler(signal, frame):
    print('Ctrl-C caught: exiting...')
    quit()

# ..............................................................................
def go(motors, velocity, slew_rate, direction, steps):

    _port_pid = motors.get_motor(Orientation.PORT).get_pid_controller()
    _stbd_pid = motors.get_motor(Orientation.STBD).get_pid_controller()

    _port_pid.set_step_limit(direction, steps)
    _tp = Thread(target=_port_pid.step_to, args=(velocity, direction, slew_rate, lambda: _port_pid.is_stepping(direction) ))
    if not _port_pid.is_stepping(direction):
        raise Exception('port pid not enabled')
    _stbd_pid.set_step_limit(direction, steps)
    _ts = Thread(target=_stbd_pid.step_to, args=(velocity, direction, slew_rate, lambda: _stbd_pid.is_stepping(direction) ))
    if not _stbd_pid.is_stepping(direction):
        raise Exception('stbd pid not enabled')

    _tp.start()
    _ts.start()
    while _port_pid.is_stepping(direction) or _stbd_pid.is_stepping(direction):
        time.sleep(0.1)
#   motors.brake()
    _tp.join()
    _ts.join()

# ..............................................................................
def main():
    '''
         Notes:

         494 encoder steps per rotation (maybe 493)
         68.5mm diameter tires
         215.19mm/21.2cm wheel circumference
         1 wheel rotation = 215.2mm
         2295 steps per meter
         2295 steps per second = 1 m/sec
         2295 steps per second = 100 cm/sec

         1 rotation = 215mm = 494 steps
         1 meter = 4.587 rotations
         2295.6 steps per meter
         229.5 steps per cm
    '''

#   signal.signal(signal.SIGINT, signal_handler)
    _log = Logger("pid-test", Level.INFO)

    _loader = ConfigLoader(Level.INFO)
    filename = 'config.yaml'
    _config = _loader.configure(filename)

    _motors = Motors(_config, None, Level.INFO)
    _port_pid = _motors.get_motor(Orientation.PORT).get_pid_controller()
    _stbd_pid = _motors.get_motor(Orientation.STBD).get_pid_controller()

    try:

        _distance_cm = 100
        _fwd_steps_per_meter = _stbd_pid.get_steps_for_distance_cm(_distance_cm)
        _log.info(Fore.MAGENTA + Style.BRIGHT + 'CALC: {:>5.2f} steps per {:d} cm.'.format(_fwd_steps_per_meter, _distance_cm) + Style.RESET_ALL)

        _forward_steps = _fwd_steps_per_meter

        _slew_rate = SlewRate.FAST
        _direction = Direction.FORWARD
        _velocity = Velocity.HALF

        _log.info(Fore.RED + 'FORWARD...                  ---------------------------------- ' + Style.RESET_ALL)
        go(_motors, _velocity, _slew_rate, Direction.FORWARD, _forward_steps)

        _log.info(Fore.RED + 'BRAKING...                  ---------------------------------- ' + Style.RESET_ALL)
        _motors.brake()

        # maintain velocity for 1 m
#       _distance_m = 2
#       _port_step_limit = _port_pid.get_steps() + _fwd_steps_per_meter * _distance_m
#       _stbd_step_limit = _stbd_motor.get_steps() + _fwd_steps_per_meter * _distance_m

#       _port_pid.maintain_velocity(_velocity, _port_step_limit)
#       _stbd_motor.maintain_velocity(_velocity, _stbd_step_limit)

#       time.sleep(1.0)
#       _log.info(Fore.RED + 'REVERSE...                  ---------------------------------- ' + Style.RESET_ALL)

#       go(_motors, _velocity, _slew_rate, Direction.REVERSE, _forward_steps)

#       _port_pid.maintain_velocity(_velocity, _port_step_limit)
#       _stbd_motor.maintain_velocity(_velocity, _stbd_step_limit)
#       _motors.brake()

        _log.info(Fore.CYAN + Style.BRIGHT + 'completed thread.' + Style.RESET_ALL)
        _log.info(Fore.CYAN + Style.BRIGHT + 'A. motor test complete; intended: {:d}; actual steps: port: {} ; stbd: {}.'.format(\
                _forward_steps, _port_pid.get_steps(), _stbd_pid.get_steps()  ) + Style.RESET_ALL)

        _port_distance_cm = _port_pid.get_distance_cm_for_steps(_port_pid.get_steps())
        _stbd_distance_cm = _stbd_pid.get_distance_cm_for_steps(_stbd_pid.get_steps())
        _log.info(Fore.CYAN + Style.BRIGHT + 'distance traveled: port: {:>5.2f}, stbd: {:>5.2f}.'.format(_port_distance_cm, _stbd_distance_cm) + Style.RESET_ALL)

    except KeyboardInterrupt:
        _log.info(Fore.CYAN + Style.BRIGHT + 'B. motor test complete; intended: {:d}; actual steps: port: {} ; stbd: {}.'.format(\
                _forward_steps, _port_pid.get_steps(), _stbd_pid.get_steps()  ) + Style.RESET_ALL)
        _stbd_motor.halt()
        quit()
    except Exception as e:
        _log.info(Fore.RED + Style.BRIGHT + 'error in PID controller: {}'.format(e))
        traceback.print_exc(file=sys.stdout)
    finally:
        _log.info(Fore.YELLOW + Style.BRIGHT + 'C. finally.')
#       _stbd_motor.halt()

if __name__== "__main__":
    main()

#EOF
