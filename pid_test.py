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

# exception handler ............................................................
def signal_handler(signal, frame):
    print('Ctrl-C caught: exiting...')
    quit()

# ..............................................................................
def go(motors, slew_rate, direction, steps):

    _port_motor = motors.get_motor(Orientation.PORT)
    _port_pid   = _port_motor.get_pid_controller()
    _stbd_motor = motors.get_motor(Orientation.STBD)
    _stbd_pid   = _stbd_motor.get_pid_controller()

    _port_pid.set_step_limit(direction, steps)
    _tp = Thread(target=_port_pid.step_to, args=(Velocity.HALF, direction, slew_rate, lambda: _port_pid.is_stepping(direction) ))
    if not _port_pid.is_stepping(direction):
        raise Exception('port pid not enabled')

    _stbd_pid.set_step_limit(direction, steps)
    _ts = Thread(target=_stbd_pid.step_to, args=(Velocity.HALF, direction, slew_rate, lambda: _stbd_pid.is_stepping(direction) ))
    if not _stbd_pid.is_stepping(direction):
        raise Exception('stbd pid not enabled')

    _tp.start()
    _ts.start()
    while _port_pid.is_stepping(direction) or _stbd_pid.is_stepping(direction):
        time.sleep(0.1)
    motors.brake()
    _tp.join()
    _ts.join()

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
         1 meter = 4.587 rotations
         2266 steps per meter
    '''
    try:

#       signal.signal(signal.SIGINT, signal_handler)


        _loader = ConfigLoader(Level.INFO)
        filename = 'config.yaml'
        _config = _loader.configure(filename)

        _motors = Motors(_config, None, Level.INFO)
        _port_motor = _motors.get_motor(Orientation.PORT)
        _stbd_motor = _motors.get_motor(Orientation.STBD)

#       _forward_steps = PID.get_forward_steps(1)
        _forward_steps = 2266
        print(Fore.MAGENTA + Style.BRIGHT + 'starting thread for {:d} steps...'.format(_forward_steps) + Style.RESET_ALL)

        _slew_rate = SlewRate.FAST
        _direction = Direction.FORWARD

        go(_motors, _slew_rate, Direction.FORWARD, _forward_steps)

        time.sleep(0.5)

        go(_motors, _slew_rate, Direction.REVERSE, _forward_steps)

        print(Fore.YELLOW + Style.BRIGHT + 'completed thread.' + Style.RESET_ALL)
        print(Fore.YELLOW + Style.BRIGHT + 'A. motor test complete; intended: {:d}; actual steps: {}.'.format(_forward_steps, _stbd_motor.get_steps()) + Style.RESET_ALL)

    except KeyboardInterrupt:
        print(Fore.YELLOW + Style.BRIGHT + 'B. motor test complete; intended: {:d}; actual steps: {}.'.format(_forward_steps, _stbd_motor.get_steps()) + Style.RESET_ALL)
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
