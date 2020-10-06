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
from lib.enums import Rotation, Direction, Speed, Orientation
from lib.velocity import Velocity
from lib.slew import SlewRate, SlewLimiter
from lib.logger import Logger, Level
from lib.config_loader import ConfigLoader
from lib.motor import Motor
from lib.motors_v2 import Motors
from lib.pid_v2 import PID
from lib.rate import Rate

# ..............................................................................
def main():

    _log = Logger("vel-test", Level.INFO)

    _loader = ConfigLoader(Level.INFO)
    filename = 'config.yaml'
    _config = _loader.configure(filename)

    _motors = Motors(_config, None, Level.INFO)
    _port_pid = _motors.get_motor(Orientation.PORT).get_pid_controller()
    _stbd_pid = _motors.get_motor(Orientation.STBD).get_pid_controller()
    _pid = _stbd_pid

    Velocity.CONFIG.configure(_config)
#   sys.exit(0)

    try:

        _trial_time_sec  = 10.0
#       _motor_power     = 0.99
        _motor_velocity  = 0.0
        _target_velocity = 80.0

#       _motors.get_motor(Orientation.PORT).get_thunderborg().SetMotor1(_motor_power) # direct to TB (max: 0.6?)
#       _motors.get_motor(Orientation.STBD).get_thunderborg().SetMotor2(_motor_power) # direct to TB (max: 0.6?)

#       _distance_cm = 100
#       _fwd_steps_per_meter = _stbd_pid.get_steps_for_distance_cm(_distance_cm)
#       _log.info(Fore.MAGENTA + Style.NORMAL + 'calculated: {:>5.2f} steps per {:d} cm.'.format(_fwd_steps_per_meter, _distance_cm))

        _current_value = 0
        _limiter = SlewLimiter(_config, Orientation.STBD, Level.INFO)
        _limiter.enable()
        _rate = Rate(5) # Hz

        _pid.reset_steps()
        _pid.enable()

        # accelerate...
#       _motors.get_motor(Orientation.PORT).accelerate_to_velocity(_motor_velocity, SlewRate.NORMAL, -1)
        while _motor_velocity < _target_velocity:
            _motor_velocity = _limiter.slew(_motor_velocity, _target_velocity)
            _pid.set_velocity(_motor_velocity)
            _log.info(Fore.CYAN + Style.BRIGHT + 'velocity: {:>5.2f} -> {:>5.2f}.'.format(_motor_velocity, _target_velocity))
            _rate.wait()
#           time.sleep(0.1)

        _log.info(Fore.GREEN + Style.BRIGHT + 'reached terminal velocity: {:>5.2f} == {:>5.2f}.'.format(_motor_velocity, _target_velocity))

#       _motors.get_motor(Orientation.PORT).set_motor_power(_motor_power)
        time.sleep(_trial_time_sec)

        # decelerate...
        _target_velocity = 0.0
        while _motor_velocity > _target_velocity:
            _motor_velocity = _limiter.slew(_motor_velocity, _target_velocity)
            _pid.set_velocity(_motor_velocity)
            _log.info(Fore.YELLOW + Style.NORMAL + 'velocity: {:>5.2f} -> {:>5.2f}.'.format(_motor_velocity, _target_velocity))
            _rate.wait()

        _pid.disable()

        time.sleep(1.0)
        _motors.brake()

#       time.sleep(1.0)
#       _motors.get_motor(Orientation.STBD).accelerate_to_velocity(_motor_velocity, SlewRate.NORMAL, -1)
#       _stbd_pid.reset_steps()
#       _motors.get_motor(Orientation.STBD).set_motor_power(_motor_power)
#       _stbd_pid.enable()
#       time.sleep(_trial_time_sec)
#       _stbd_pid.disable()
#       _motors.brake()

        # output results of test:
        _log.info(Fore.MAGENTA + Style.BRIGHT + 'max diff steps: {:d} steps per loop @ motor velocity of {:5.2f}'.format(_pid.get_max_diff_steps(), _motor_velocity))
#       _log.info(Fore.MAGENTA + Style.BRIGHT + 'STBD max diff steps: {:d} steps per loop @ motor velocity of {:5.2f}'.format(_stbd_pid.get_max_diff_steps(), _motor_velocity))
        sys.exit(0)

#       _forward_steps = _fwd_steps_per_meter

#       _slew_rate = SlewRate.FAST
#       _direction = Direction.FORWARD
#       _velocity = Velocity.HALF

#       _log.info(Fore.RED + 'FORWARD...                  ---------------------------------- ')
#       go(_motors, _velocity, _slew_rate, Direction.FORWARD, _forward_steps)

#       _log.info(Fore.RED + 'BRAKING...                  ---------------------------------- ')

        # maintain velocity for 1 m
#       _distance_m = 2
#       _port_step_limit = _port_pid.get_steps() + _fwd_steps_per_meter * _distance_m
#       _stbd_step_limit = _stbd_motor.get_steps() + _fwd_steps_per_meter * _distance_m

#       _port_pid.maintain_velocity(_velocity, _port_step_limit)
#       _stbd_motor.maintain_velocity(_velocity, _stbd_step_limit)

#       time.sleep(1.0)
#       _log.info(Fore.RED + 'REVERSE...                  ---------------------------------- ')

#       go(_motors, _velocity, _slew_rate, Direction.REVERSE, _forward_steps)

#       _port_pid.maintain_velocity(_velocity, _port_step_limit)
#       _stbd_motor.maintain_velocity(_velocity, _stbd_step_limit)
#       _motors.brake()

        _log.info(Fore.CYAN + Style.BRIGHT + 'completed thread.')
#       _log.info(Fore.CYAN + Style.BRIGHT + 'A. motor test complete; intended: {:d}; actual steps: port: {} ; stbd: {}.'.format(_forward_steps, _pid.get_steps(), _stbd_pid.get_steps()))

        _distance_cm = _pid.get_distance_cm_for_steps(_pid.get_steps())
        _log.info(Fore.CYAN + Style.BRIGHT + 'distance traveled: {:>5.2f}.'.format(_distance_cm))
#       _port_distance_cm = _port.get_distance_cm_for_steps(_pid.get_steps())
#       _stbd_distance_cm = _stbd_pid.get_distance_cm_for_steps(_stbd_pid.get_steps())
#       _log.info(Fore.CYAN + Style.BRIGHT + 'distance traveled: port: {:>5.2f}, stbd: {:>5.2f}.'.format(_port_distance_cm, _stbd_distance_cm))

    except KeyboardInterrupt:
        _log.info(Fore.CYAN + Style.BRIGHT + 'B. motor test complete; intended: {:d}; actual steps: port: {} ; stbd: {}.'.format(\
                _forward_steps, _port_pid.get_steps(), _stbd_pid.get_steps()))
        _stbd_motor.halt()
    except Exception as e:
        _log.info(Fore.RED + Style.BRIGHT + 'error in PID controller: {}'.format(e))
        traceback.print_exc(file=sys.stdout)
    finally:
        _log.info(Fore.YELLOW + Style.BRIGHT + 'C. finally.')
#       _stbd_motor.halt()
        quit()

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

# ..............................................................................
def quit():
    Motor.cancel()
    sys.stderr = DevNull()
    print('exit.')
    sys.exit(0)

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



if __name__== "__main__":
    main()

#EOF
