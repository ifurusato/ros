#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# Copyright 2020 by Murray Altheim. All rights reserved. This file is part of
# the Robot OS project and is released under the "Apache Licence, Version 2.0".
# Please see the LICENSE file included as part of this package.
#
# author:   Murray Altheim
# created:  2020-08-22
# modified: 2020-08-22
#
#  Testing rotation based on compass orientation. Currently unfinished.
#

import os, sys, signal, time, traceback, itertools
from threading import Thread
from fractions import Fraction
from colorama import init, Fore, Style
init()

from lib.devnull import DevNull
from lib.enums import Rotation, Direction, Speed, Velocity, SlewRate, Orientation
from lib.logger import Logger, Level
from lib.config_loader import ConfigLoader
from lib.queue import MessageQueue
from lib.motor import Motor
from lib.motors import Motors
from lib.indicator import Indicator
from lib.compass import Compass

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

def get_forward_steps():
    _rotations = 5
    _forward_steps_per_rotation = 494
    _forward_steps = _forward_steps_per_rotation * _rotations
    return _forward_steps

def _spin(motors, rotation, f_is_enabled):
    print('motors spin {}.'.format(rotation))

    _port_motor = motors.get_motor(Orientation.PORT)
    _port_pid   = _port_motor.get_pid_controller()
    _stbd_motor = motors.get_motor(Orientation.STBD)
    _stbd_pid   = _stbd_motor.get_pid_controller()

    _forward_steps = get_forward_steps()
    if rotation is Rotation.CLOCKWISE:
        _tp = Thread(target=_port_pid.step_to, args=(Velocity.TWO_THIRDS, Direction.FORWARD, SlewRate.SLOW, _forward_steps, f_is_enabled))
        _ts = Thread(target=_stbd_pid.step_to, args=(Velocity.TWO_THIRDS, Direction.FORWARD, SlewRate.SLOW, _forward_steps, f_is_enabled))
#           self._port_pid.step_to(Velocity.TWO_THIRDS, Direction.FORWARD, SlewRate.SLOW, _forward_steps, f_is_enabled)
#           self._stbd_pid.step_to(Velocity.TWO_THIRDS, Direction.REVERSE, SlewRate.SLOW, _forward_steps, f_is_enabled)
    else: # COUNTER_CLOCKWISE 
        _tp = Thread(target=_port_pid.step_to, args=(Velocity.TWO_THIRDS, Direction.FORWARD, SlewRate.SLOW, _forward_steps, f_is_enabled))
        _ts = Thread(target=_stbd_pid.step_to, args=(Velocity.TWO_THIRDS, Direction.FORWARD, SlewRate.SLOW, _forward_steps, f_is_enabled))
#           self._port_pid.step_to(Velocity.TWO_THIRDS, Direction.REVERSE, SlewRate.SLOW, _forward_steps, f_is_enabled)
#           self._stbd_pid.step_to(Velocity.TWO_THIRDS, Direction.FORWARD, SlewRate.SLOW, _forward_steps, f_is_enabled)
    _tp.start()
    _ts.start()
    _tp.join()
    _ts.join()
#       self.print_current_power_levels()
    print('complete: motors spin {}.'.format(rotation))


# ..............................................................................
def has_heading(compass, expected_heading):
    '''
        Returns true if the current compass heading is within an error range of the expected value.
    '''
    err = 1.0
    if ( expected_heading - err ) < compass.get_heading() < ( expected_heading + err ):
        return True
    return False


# ..............................................................................
def main():
    try:

#       signal.signal(signal.SIGINT, signal_handler)

        _wheel_circumference_mm = 218
        _forward_steps_per_rotation = 494
        _forward_steps = get_forward_steps()

        _loader = ConfigLoader(Level.INFO)
        filename = 'config.yaml'
        _config = _loader.configure(filename)
        
        _queue = MessageQueue(Level.INFO)
        _indicator = Indicator(Level.INFO)
        _compass = Compass(_config, _queue, _indicator, Level.INFO)
        _compass.enable()

        print(Fore.CYAN + Style.BRIGHT + 'wave robot in the air until calibrated.' + Style.RESET_ALL)
        while not _compass.is_calibrated():
            time.sleep(0.33)

        print(Fore.CYAN + Style.BRIGHT + 'CALIBRATED.      xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx ' + Style.RESET_ALL)
        time.sleep(5.0)

        _motors = Motors(_config, None, None, Level.INFO)
#       _port_motor = _motors.get_motor(Orientation.PORT)
#       _stbd_motor = _motors.get_motor(Orientation.STBD)

        _heading = 0.0 # due south
        _spin(_motors, Rotation.CLOCKWISE, lambda: not has_heading(_compass, _heading) ) 

        print(Fore.CYAN + Style.BRIGHT + 'test complete.' + Style.RESET_ALL)

    except KeyboardInterrupt:
        _stbd_motor.halt()
        quit()
    except Exception as e:
        print(Fore.RED + Style.BRIGHT + 'error in PID controller: {}'.format(e) + Style.RESET_ALL)
        traceback.print_exc(file=sys.stdout)
    finally:
        print(Fore.YELLOW + Style.BRIGHT + 'C. finally.' + Style.RESET_ALL)


# ..............................................................................
if __name__== "__main__":
    main()

#EOF
