#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# Copyright 2020 by Murray Altheim. All rights reserved. This file is part of
# the Robot OS project and is released under the "Apache Licence, Version 2.0".
# Please see the LICENSE file included as part of this package.
#

# Import library functions we need
import os, sys, signal, time, threading, traceback
from fractions import Fraction
from colorama import init, Fore, Style
init()

try:
    import numpy
except ImportError:
    exit("This script requires the numpy module\nInstall with: sudo pip3 install numpy")

from lib.devnull import DevNull
from lib.enums import Direction, Speed, Velocity, SlewRate, Orientation
from lib.logger import Logger, Level
from lib.config_loader import ConfigLoader
from lib.motor import Motor
from lib.motors import Motors
from lib.filewriter import FileWriter

_port_motor = None
_stbd_motor = None

def quit():
    if _port_motor:
        _port_motor.halt()
    if _stbd_motor:
        _stbd_motor.halt()
    Motor.cancel()
    sys.stderr = DevNull()
    print('exit.')
    sys.exit(0)

# exception handler ........................................................
def signal_handler(signal, frame):
    print('Ctrl-C caught: exiting...')
    quit()

# ..............................................................................
def main():
    '''
         494 encoder steps per rotation (maybe 493)
         218mm wheel circumference
         1 wheel rotation = 218mm
         2262 steps per meter
         2262 steps per second = 1 m/sec
         2262 steps per second = 100 cm/sec

         Notes:
         1 rotation = 218mm = 493 steps
    '''
    try:

#       signal.signal(signal.SIGINT, signal_handler)

        _wheel_circumference_mm = 218
        _forward_steps_per_rotation = 494
        _reverse_steps_per_rotation = 494

        _loader = ConfigLoader(Level.INFO)
        filename = 'config.yaml'
        _config = _loader.configure(filename)

        _motors = Motors(_config, None, None, Level.INFO)
        # disable port motor ............................
        _port_motor = _motors.get_motor(Orientation.PORT)
        _port_motor.set_motor_power(0.0)

        _stbd_motor = _motors.get_motor(Orientation.STBD)
        _filewriter = FileWriter(_config, 'pid', Level.INFO)

        _pid = _stbd_motor.get_pid_controller()
        _pid.set_filewriter(_filewriter)

        _rotations = 5
        _forward_steps = _forward_steps_per_rotation * _rotations
        print(Fore.YELLOW + Style.BRIGHT + 'starting forward motor test for steps: {:d}.'.format(_forward_steps) + Style.RESET_ALL)
        _pid.step_to(Velocity.TWO_THIRDS, Direction.FORWARD, SlewRate.SLOW, _forward_steps)

        _rotations = 3
        _forward_steps = _forward_steps_per_rotation * _rotations
        _pid.step_to(Velocity.HALF, Direction.FORWARD, SlewRate.SLOW, _forward_steps)

        _pid.close_filewriter()
        _stbd_motor.brake()
        _stbd_motor.close()

        print(Fore.YELLOW + Style.BRIGHT + 'A. motor test complete; intended: {:d}; actual steps: {:d}.'.format(_forward_steps, _stbd_motor.get_steps()) + Style.RESET_ALL)

    except KeyboardInterrupt:
        print(Fore.YELLOW + Style.BRIGHT + 'B. motor test complete; intended: {:d}; actual steps: {:d}.'.format(_forward_steps, _stbd_motor.get_steps()) + Style.RESET_ALL)
        _stbd_motor.halt()
        quit()
    except Exception as e:
        print(Fore.RED + Style.BRIGHT + 'error in PID controller: {}'.format(e))
        traceback.print_exc(file=sys.stdout)
    finally:
        print(Fore.YELLOW + Style.BRIGHT + 'C. finally.')
#       _stbd_motor.halt()

if __name__== "__main__":
    main()


#EOF
