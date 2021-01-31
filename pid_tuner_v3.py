#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# Copyright 2020 by Murray Altheim. All rights reserved. This file is part of
# the Robot OS project and is released under the "Apache Licence, Version 2.0".
# Please see the LICENSE file included as part of this package.
#
# A quick test of the simple_pid library.

import sys, traceback, time, itertools
from colorama import init, Fore, Style
init()

from lib.velocity import Velocity
from lib.logger import Logger, Level
from lib.config_loader import ConfigLoader
from lib.slew import SlewRate, SlewLimiter
from lib.motors import Motors
from lib.motor import Motor
from lib.enums import Orientation
from lib.rate import Rate
from lib.pot import Potentiometer

from lib.pid_v3 import PID

# ..............................................................................
def main():

    _log = Logger('main', Level.INFO)
    _rate = Rate(20) # Hz

    _loader = ConfigLoader(Level.INFO)
    filename = 'config.yaml'
    _config = _loader.configure(filename)
#   Velocity.CONFIG.configure(_config)
    _pot = Potentiometer(_config, Level.INFO)
#   _pot.set_out_max(3.0)

    try:

        # motors ...............................................................
        _motors = Motors(_config, None, Level.INFO)
        _port_motor = _motors.get_motor(Orientation.PORT)
        _stbd_motor = _motors.get_motor(Orientation.STBD)
#       _motor = _stbd_motor

        # pid ..................................................................
        _pid_config = _config['ros'].get('motors').get('pid')

        _target_velocity = 0.0

        _port_pid = PID(_config, setpoint=_target_velocity, sample_time=_rate.get_period_sec(), level=Level.INFO)
        _stbd_pid = PID(_config, setpoint=_target_velocity, sample_time=_rate.get_period_sec(), level=Level.INFO)

#       _stbd_pid.auto_mode = True
#       _stbd_pid.proportional_on_measurement = True
#       _stbd_pid.set_auto_mode(False)
#       _stbd_pid.tunings = ( _kp, _ki, _kd )
#       _stbd_pid.output_limits = ( -10.0, 10.0 )
#       _stbd_pid.sample_time = _rate.get_period_sec()
#       _log.info(Fore.GREEN + 'sample time: {:>6.3f} sec.'.format(_stbd_pid.sample_time))

#       _clip_max = 1.0
#       _clip_min = -1.0 * _clip_max
#       _clip = lambda n: _clip_min if n <= _clip_min else _clip_max if n >= _clip_max else n
#       _limiter = SlewLimiter(_config, None, Level.WARN)
#       _limiter.enable()
#       _stbd_pid.setpoint = _target_velocity

        _kp = 0.0
        _ki = 0.0
        _kd = 0.0
        _power = 0.0
        _limit = -1
        _count = -1

        try:
            while True: 
                _count = 0
                _counter = itertools.count()
                while _limit < 0 or _count < _limit:

                    _count = next(_counter)
                    _pot_value = _pot.get_scaled_value()
                    _target_velocity = _pot_value

                    _port_pid.setpoint = _target_velocity
#                   _port_pid.tunings = ( _kp, _ki, _kd )
                    _last_power = _port_motor.get_current_power_level()
                    _current_velocity = _port_motor.get_velocity()
                    _power += _port_pid(_current_velocity) / 100.0
                    _set_power = _power / 100.0
                    _port_motor.set_motor_power(_power)
                    # .........................
                    kp, ki, kd = _port_pid.constants
                    print(Fore.RED + '{:d}\tPID:{:6.3f}|{:6.3f}|{:6.3f};\tLAST={:>7.4f}\tSET={:>7.4f};  \tvel: {:>6.3f}/{:>6.3f}'.format(\
                            _count, kp, ki, kd, _last_power, _power, _current_velocity, _target_velocity) + Style.RESET_ALL)

                    _stbd_pid.setpoint = _target_velocity
#                   _stbd_pid.tunings = ( _kp, _ki, _kd )
                    _last_power = _stbd_motor.get_current_power_level()
                    _current_velocity = _stbd_motor.get_velocity()
                    _power += _stbd_pid(_current_velocity) / 100.0
#                   _set_power = _power / 100.0
                    _stbd_motor.set_motor_power(_power)
                    # .........................
                    kp, ki, kd = _stbd_pid.constants
                    print(Fore.GREEN + '{:d}\tPID:{:6.3f}|{:6.3f}|{:6.3f};\tLAST={:>7.4f}\tSET={:>7.4f};  \tvel: {:>6.3f}/{:>6.3f}'.format(\
                            _count, kp, ki, kd, _last_power, _power, _current_velocity, _target_velocity) + Style.RESET_ALL)

                    _rate.wait()

                _motors.brake()
                time.sleep(1.0)

        except KeyboardInterrupt:
            _log.info(Fore.CYAN + Style.BRIGHT + 'B. motor test complete.')
        finally:
            _motors.brake()

        '''
        Kpro = 0.380
        Kdrv = 0.0
        last_proportional_error = 0.0
        power = 0.0
        while True:
            Kdrv = _pot.get_scaled_value()
            _current_velocity = _motor.get_velocity()
            proportional_error = _target_velocity - _current_velocity
            derivative_error = proportional_error - last_proportional_error
            last_proportional_error = proportional_error
            power += (proportional_error * Kpro) + (derivative_error * Kdrv)
            _motor.set_motor_power( power / 100.0 )
            _log.info(Fore.GREEN + ' P:{:6.3f}; D:{:6.3f};'.format(Kpro, Kdrv) \
                    + Fore.YELLOW + ' power: {:>8.5f};'.format(power) \
                    + Fore.MAGENTA + ' velocity: {:>6.3f}/{:>6.3f}'.format(_current_velocity, _target_velocity))
            _rate.wait()
        '''




    except Exception as e:
        _log.info(Fore.RED + Style.BRIGHT + 'error in PID controller: {}'.format(e))
        traceback.print_exc(file=sys.stdout)
    finally:
        _log.info(Fore.YELLOW + Style.BRIGHT + 'C. finally.')
#       _pid.disable()
#       _pid.close()



if __name__== "__main__":
    main()

#EOF
