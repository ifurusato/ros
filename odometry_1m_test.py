#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# Copyright 2020 by Murray Altheim. All rights reserved. This file is part of
# the Robot OS project and is released under the "Apache Licence, Version 2.0".
# Please see the LICENSE file included as part of this package.
#

import os, sys, signal, time, threading
from fractions import Fraction
from colorama import init, Fore, Style
init()

from lib.devnull import DevNull
from lib.enums import Speed, SlewRate, Orientation
from lib.logger import Logger, Level
from lib.config_loader import ConfigLoader
from lib.motor import Motor
from lib.motors import Motors

# exception handler ........................................................
def signal_handler(signal, frame):
    print('Ctrl-C caught: exiting...')
    Motor.cancel()
    sys.stderr = DevNull()
    print('exit.')
    sys.exit(0)

_motors = None

# ..............................................................................
def main():
    '''
         494 encoder steps per rotation (maybe 493)
         218mm wheel circumference
         1 wheel rotation = 218mm
         2262 steps per meter
         2262 steps per second = 1 m/sec
         2262 steps per second = 100 cm/sec

    '''
    STEPS_PER_METER = 2262
    _wheel_circumference_mm = 218
    _forward_steps_per_rotation = 494
    _reverse_steps_per_rotation = 494

    signal.signal(signal.SIGINT, signal_handler)

    try:
        _loader = ConfigLoader(Level.INFO)
        filename = 'config.yaml'
        _config = _loader.configure(filename)

        _speed = 70.0

        _motors = Motors(_config, None, None, Level.DEBUG)
        _port_motor = _motors.get_motor(Orientation.PORT)
        _stbd_motor = _motors.get_motor(Orientation.STBD)
        _motors.enable()

        _rotations = 3
        forward_test = True
        if forward_test:
            #_forward_steps_per_rotation * _rotations
            _forward_steps = int(1.0 * STEPS_PER_METER)

            print(Fore.YELLOW + Style.BRIGHT + 'starting forward motor test for steps: {:d}.'.format(_forward_steps) + Style.RESET_ALL)
            while not _motors.ahead_for_steps(_speed, _speed, _forward_steps, _forward_steps):
                time.sleep(0.1)

            time.sleep(2.0)

#           _speed = -1 * _speed
#           while not _motors.ahead_for_steps(_speed, _speed, _forward_steps, _forward_steps):
#               time.sleep(0.1)

            print(Fore.YELLOW + Style.BRIGHT + 'motor test complete; intended: {:d}; actual steps: {:d}/{:d}.'.format(\
                    _forward_steps, _port_motor.get_steps(), _stbd_motor.get_steps()) + Style.RESET_ALL)

        else:
            _reverse_steps = _reverse_steps_per_rotation * _rotations
            print(Fore.YELLOW + Style.BRIGHT + 'starting reverse motor test for steps: {:d}.'.format(_reverse_steps) + Style.RESET_ALL)
#           _stbd_motor.ahead_for_steps(-30.0, _reverse_steps)
#           _stbd_motor.stop()
#           print(Fore.YELLOW + Style.BRIGHT + 'motor test complete; intended: {:d}; actual steps: {:d}.'.format(\
#                   _reverse_steps, _stbd_motor.get_steps()) + Style.RESET_ALL)

    except KeyboardInterrupt:
        print('Ctrl-C caught, exiting...')
    finally:
        if _motors:
            _motors.brake()

if __name__== "__main__":
    main()


#EOF
