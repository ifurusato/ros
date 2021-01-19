#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# Copyright 2020 by Murray Altheim. All rights reserved. This file is part of
# the Robot OS project and is released under the "Apache Licence, Version 2.0".
# Please see the LICENSE file included as part of this package.
#
# author:   Murray Altheim
# created:  2020-04-20
# modified: 2020-09-26
#
# This controller uses a threaded loop and uses a pair of PID controllers from
# the PID class.
#

import sys, itertools
from collections import deque as Deque
from threading import Thread
from enum import Enum
from colorama import init, Fore, Style
init()

from lib.logger import Logger, Level
from lib.pid import PID
from lib.slew import SlewRate, SlewLimiter
from lib.rate import Rate
from lib.pot import Potentiometer

# ..............................................................................
class PIDController(object):
    '''
     Provides a configurable PID motor controller via a threaded
     fixed-time loop.

     If the 'ros:motors:pid:enable_slew' property is True, this will set a slew
     limiter on the velocity setter.
    '''

    def __init__(self,
                 config,
                 motor,
                 setpoint=0.0,
                 sample_time=0.01,
                 level=Level.INFO):
        '''
        :param config:       The application configuration, read from a YAML file.
        :param motor:        The motor to be controlled.
        :param setpoint:     The initial setpoint or target output
        :param sample_time:  The time in seconds before generating a new output value.
                             This PID is expected to be called at a constant rate.
        :param level:        The log level, e.g., Level.INFO.
        '''
        if motor is None:
            raise ValueError('null motor argument.')
        self._motor = motor
        self._log = Logger('pid-ctrl:{}'.format(motor.orientation.label), level)
        if sys.version_info < (3,0):
            self._log.error('PID class requires Python 3.')
            sys.exit(1)
        # PID configuration ................................
        if config is None:
            raise ValueError('null configuration argument.')
        _config = config['ros'].get('motors').get('pid-controller')
        self._pot_ctrl = _config.get('pot_ctrl')
        if self._pot_ctrl:
            self._pot = Potentiometer(config, Level.INFO)
        self._rate = Rate(_config.get('sample_freq_hz'), level)
        _sample_time = self._rate.get_period_sec()
        self._pid = PID(config, self._motor.orientation, sample_time=_sample_time, level=level)

        # used for hysteresis, if queue too small will zero-out motor power too quickly
        _queue_len = _config.get('hyst_queue_len')
        self._deque = Deque([], maxlen=_queue_len)

        self._enable_slew = True #_config.get('enable_slew')
        self._slewlimiter = SlewLimiter(config, orientation=self._motor.orientation, level=Level.INFO)
        _slew_rate = SlewRate.NORMAL # TODO _config.get('slew_rate')
        self._slewlimiter.set_rate_limit(_slew_rate)
        if self._enable_slew:
            self._slewlimiter.enable()
            self._log.info('slew limiter enabled.')
        else:
            self._log.info('slew limiter disabled.')

        self._power      = 0.0
        self._last_power = 0.0
        self._failures   = 0
        self._enabled    = False
        self._disabling  = False
        self._closed     = False
        self._thread     = None
#       self._last_steps = 0
#       self._max_diff_steps = 0
        self._log.info('ready.')

    # ..........................................................................
    @property
    def orientation(self):
        return self._motor.orientation

    # ..............................................................................
    def enable_slew(self, enable):
        _old_value = self._enable_slew
        if not self._slewlimiter.is_enabled():
            self._slewlimiter.enable()
        self._enable_slew = enable
        return _old_value

    # ..............................................................................
    def set_slew_rate(self, slew_rate):
        if type(slew_rate) is SlewRate:
            self._slewlimiter.set_rate_limit(slew_rate)
        else:
            raise Exception('expected SlewRate argument, not {}'.format(type(slew_rate)))

    # ..............................................................................
    @property
    def steps(self):
        return self._motor.steps

    def reset_steps(self):
        self._motor._steps = 0

    # ..........................................................................
    @property
    def velocity(self):
        '''
        Getter for the velocity (PID set point).
        '''
        return self._pid.velocity

    @velocity.setter
    def velocity(self, velocity):
        '''
        Setter for the velocity (PID set point).
        '''
        if self._enable_slew:
            velocity = self._slewlimiter.slew(self.velocity, velocity)
        self._pid.velocity = velocity

    # ..........................................................................
    def set_max_velocity(self, max_velocity):
        '''
        Setter for the maximum velocity of both PID controls. Set
        to None (the default) to disable this feature.
        '''
#       if max_velocity == None:
#           self._log.info(Fore.YELLOW + 'max velocity: NONE')
#       else:
#           self._log.info(Fore.YELLOW + 'max velocity: {:5.2f}'.format(max_velocity))
        self._pid.set_max_velocity(max_velocity)

    # ..........................................................................
    @property
    def stats(self):
        '''
         Returns statistics a tuple for this PID contrroller:
            [kp, ki, kd, cp, ci, cd, last_power, current_motor_power, power, current_velocity, setpoint, steps]
        '''
        kp, ki, kd = self._pid.constants
        cp, ci, cd = self._pid.components
        return kp, ki, kd, cp, ci, cd, self._last_power, self._motor.get_current_power_level(), self._power, self._motor.velocity, self._pid.setpoint, self._motor.steps

    # ..........................................................................
    @property
    def enabled(self):
        return self._enabled

    # ..........................................................................
    def _loop(self, f_is_enabled):
        '''
        The PID loop that continues while the enabled flag is True.

        This uses a running average on the setpoint to settle the output 
        at zero when it's clear the target velocity is zero. This is a
        perhaps cheap approach to hysteresis.
        '''
        _doc = Documentation.SIMPLE
        _power_color = Fore.BLACK
        _lim = 0.2
        _last_velocity = 0.0
        _counter = itertools.count()

        while f_is_enabled() and self._motor.enabled:
            _count = next(_counter)
            _current_velocity = self._motor.velocity
            if self._pot_ctrl:
                _pot_value = self._pot.get_scaled_value()
                self._pid.kd = _pot_value
                self._log.debug('pot: {:8.5f}.'.format(_pot_value))
            _pid_output = self._pid(_current_velocity)
            self._power += _pid_output
            _mean_setpoint = self._get_mean_setpoint(self._pid.setpoint)
            self._log.debug('cv: {:5.2f}; pow: {:5.2f}; sp: {:5.2f}; msp: {:5.2f};'.format(_current_velocity, self._power, self._pid.setpoint, _mean_setpoint))
            if _mean_setpoint == 0.0:
                self._motor.set_motor_power(0.0)
            else:
                self._motor.set_motor_power(self._power / 100.0)

            if _doc is Documentation.MINIMAL:
                self._log.info('velocity: {:>5.2f}\t{:<5.2f}'.format(_current_velocity, self._pid.setpoint))

            elif _doc is Documentation.SIMPLE:
                if ( _last_velocity * 0.97 ) <= _current_velocity <= ( _last_velocity * 1.03 ): # within 3%
                    _velocity_color = Fore.YELLOW + Style.NORMAL
                elif _last_velocity < _current_velocity:
                    _velocity_color = Fore.MAGENTA + Style.NORMAL
                elif _last_velocity > _current_velocity:
                    _velocity_color = Fore.CYAN + Style.NORMAL
                else:
                    _velocity_color = Fore.BLACK
#               self._log.info('velocity:\t' + _velocity_color + '{:>5.2f}\t{:<5.2f}'.format(_current_velocity, self._pid.setpoint))
                self._log.info('cv: {:5.2f}; pow: {:5.2f}; sp: {:5.2f}; msp: {:5.2f};'.format(_current_velocity, self._power, self._pid.setpoint, _mean_setpoint))

            elif _doc is Documentation.FULL:
                if self._last_power < self._power:
                    _power_color = Fore.GREEN + Style.BRIGHT
                elif self._last_power > self._power:
                    _power_color = Fore.RED
                else:
                    _power_color = Fore.YELLOW
                if ( _last_velocity * 0.97 ) <= _current_velocity <= ( _last_velocity * 1.03 ): # within 3%
                    _velocity_color = Fore.YELLOW + Style.NORMAL
                elif _last_velocity < _current_velocity:
                    _velocity_color = Fore.MAGENTA + Style.NORMAL
                elif _last_velocity > _current_velocity:
                    _velocity_color = Fore.CYAN + Style.NORMAL
                else:
                    _velocity_color = Fore.BLACK

                _current_power = self._motor.get_current_power_level()
                kp, ki, kd = self._pid.constants
                cp, ci, cd = self._pid.components
                self._log.info(Fore.BLUE + 'cp={:7.4f}|ci={:7.4f}|cd={:7.4f}'.format(cp, ci, cd)\
                        + Fore.CYAN + '|kd={:<7.4f} '.format(kd) \
                        + _power_color + '\tpwr: {:>5.2f}/{:<5.2f}'.format(_current_power, self._power)\
                        + _velocity_color + '\tvel: {:>5.2f}/{:<5.2f}'.format(_current_velocity, self._pid.setpoint))

            elif _doc is Documentation.CSV:
                kp, ki, kd = self._pid.constants
                cp, ci, cd = self._pid.components
                self._log.info('{:7.4f}|{:7.4f}|{:7.4f}'.format(kp, ki, kd)\
                        + '|{:7.4f}|{:7.4f}|{:7.4f}'.format(cp, ci, cd) \
                        + '|{:>5.2f}|{:<5.2f}'.format(_current_power, self._power)\
                        + '|{:>5.2f}|{:<5.2f}'.format(_current_velocity, self._pid.setpoint))

            self._last_power = self._power
            _last_velocity = _current_velocity
            self._rate.wait() # 20Hz
            # ......................

        self._log.info('exited PID loop.')

    # ..........................................................................
    def _get_mean_setpoint(self, value):
        '''
        Returns the mean of setpoint values collected in the queue.
        This is used to provide hysteresis around the PID controller's 
        setpoint, eliminating jitter particularly around zero.
        '''
        if value == None:
            raise Exception('null argument')
        self._deque.append(value)
        _n = 0
        _mean = 0.0
        for x in self._deque:
            _n += 1
            _mean += ( x - _mean ) / _n
        return float('nan') if _n < 1 else _mean

    # ..........................................................................
    def reset(self):
        self._pid.velocity = 0.0
        self._pid.reset()
#       self._motor.reset_steps()
        self._motor.stop()
        self._log.info(Fore.GREEN + 'reset.')

    # ..........................................................................
    def enable(self):
        if not self._closed:
            if self._enabled:
                self._log.warning('PID loop already enabled.')
                return
            self._log.info('enabling PID loop...')
            self._enabled = True
            # if we haven't started the thread yet, do so now...
            if self._thread is None:
                self._thread = Thread(name = 'pid-ctrl:{}'.format(self._motor.orientation.label), \
                        target=PIDController._loop, args=[self, lambda: self.enabled])
                self._thread.start()
                self._log.info(Style.BRIGHT + 'PID loop enabled.')
            else:
                self._log.warning('cannot enable PID loop: thread already exists.')
        else:
            self._log.warning('cannot enable PID loop: already closed.')

    # ..........................................................................
    def disable(self):
        if self._disabling:
            self._log.warning('already disabling.')
            return
        elif self._closed:
            self._log.warning('already closed.')
            return
        self._enabled = False
        self._disabling = True
#       time.sleep(0.06) # just a bit more than 1 loop in 20Hz
#       if self._thread is not None:
#           self._thread.join(timeout=1.0)
#           self._log.debug('pid thread joined.')
        self._thread = None
        self._disabling = False
        self._log.info('disabled.')

    # ..........................................................................
    def close(self):
        if self._enabled:
            self.disable()
        self._closed = True
#       self.close_filewriter()
        self._log.info('closed.')

# ..............................................................................
class Documentation(Enum):
    '''
    Different documentation modes:
    '''
    NONE    = 0
    MINIMAL = 1
    SIMPLE  = 2
    FULL    = 3
    CSV     = 4

#EOF
