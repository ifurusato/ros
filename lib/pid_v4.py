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
# This PID controller is comprised of a PIDController class that includes a
# threaded loop, and a PID class providing the actual control function. This
# was derived from ideas gleaned from libraries by both Martin Lundberg and
# Brett Beauregard, as well as discussions with David Anderson of the DPRG.
#

import sys, time, threading, itertools
from enum import Enum
from colorama import init, Fore, Style
init()

from lib.config_loader import ConfigLoader
from lib.logger import Logger, Level
from lib.motor_v2 import Motor
from lib.slew import SlewRate, SlewLimiter
from lib.velocity import Velocity
from lib.rate import Rate
from lib.pot import Potentiometer

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

# ..............................................................................
class PID(object):
    '''
       The PID controller itself.
    '''
    def __init__(self,
                 config,
                 orientation, # used only for logging
                 setpoint=0.0,
                 sample_time=0.01,
                 level=Level.INFO):
        if config is None:
            raise ValueError('null configuration argument.')
        _config = config['ros'].get('motors').get('pid')
        self.kp            = _config.get('kp') # proportional gain
        self.ki            = _config.get('ki') # integral gain
        self.kd            = _config.get('kd') # derivative gain
        self._min_output   = _config.get('min_output')
        self._max_output   = _config.get('max_output')
        self._setpoint     = setpoint
        self._orientation  = orientation
        self._max_velocity = None
        self._log = Logger('pid:{}'.format(orientation.label), level)
        self._log.info('kp:{:7.4f}; ki:{:7.4f}; kd:{:7.4f};\tmin={:>5.2f}; max={:>5.2f}'.format(self._kp, self.ki, self.kd, self._min_output, self._max_output))
        if sample_time is None:
            raise Exception('no sample time argument provided')
        self._sample_time  = sample_time
        self._log.info('sample time: {:7.4f} sec'.format(self._sample_time))
        self._current_time  = time.monotonic # to ensure time deltas are always positive
        self.reset()
        self._log.info('ready.')

    # ..........................................................................
    @property
    def kp(self):
        return self._kp

    @kp.setter
    def kp(self, kp):
        self._kp = kp

    # ..........................................................................
    @property
    def ki(self):
        return self._ki

    @ki.setter
    def ki(self, ki):
        self._ki = ki

    # ..........................................................................
    @property
    def kd(self):
        return self._kd

    @kd.setter
    def kd(self, kd):
        self._kd = kd

    # ..........................................................................
    @property
    def velocity(self):
        '''
           Getter for the velocity (PID set point).
        '''
        return self.setpoint

    @velocity.setter
    def velocity(self, velocity):
        '''
           Setter for the velocity (PID set point).
        '''
        self._log.debug(Fore.BLACK + 'set velocity: {:5.2f}'.format(velocity))
        self._setpoint = velocity

    def set_max_velocity(self, max_velocity):
        '''
           Setter for the maximum velocity. Set to None (the default) to
           disable this feature. Note that this doesn't affect the setting
           of the velocity but rather the getting of the setpoint.
        '''
        if max_velocity:
            self._log.debug(Fore.CYAN + 'max velocity: {:5.2f}'.format(max_velocity))
        else:
            self._log.debug(Fore.CYAN + Style.DIM + 'max velocity: DISABLED')
        self._max_velocity = max_velocity

    # ..........................................................................
    @property
    def setpoint(self):
        '''
           The setpoint used by the controller as a tuple: (Kp, Ki, Kd)
           If a maximum velocity has been set the returned value is 
           limited by the set value.
        '''
        if self._max_velocity:
            return min(self._max_velocity, self._setpoint)
        else:
            return self._setpoint

    @setpoint.setter
    def setpoint(self, setpoint):
        '''
           Setter for the set point.
        '''
        self._setpoint = setpoint

    # ..........................................................................
    def __call__(self, target, dt=None):
        '''
           Call the PID controller with *target* and calculate and return a
           control output if sample_time seconds has passed since the last
           update. If no new output is calculated, return the previous output
           instead (or None if no value has been calculated yet).

           :param dt: If set, uses this value for timestep instead of real
                   time. This can be used in simulations when simulation time
                   is different from real time.
        '''
        _now = self._current_time()
        if dt is None:
            dt = _now - self._last_time if _now - self._last_time else 1e-16
        elif dt <= 0:
            raise ValueError("dt has nonpositive value {}. Must be positive.".format(dt))

        if dt < self._sample_time and self._last_output is not None:
            # only update every sample_time seconds
            return self._last_output

        # compute error terms
        error = self.setpoint - target
        d_input = target - (self._last_input if self._last_input is not None else target)

        # compute the proportional term
        self._proportional = self.kp * error

        # compute integral and derivative terms
        self._integral += self.ki * error * dt
        self._integral = self.clamp(self._integral)  # avoid integral windup

        self._derivative = -self.kd * d_input / dt

        # compute output
        output = self._proportional + self._integral + self._derivative
        output = self.clamp(output)

#       kp, ki, kd = self.constants
#       cp, ci, cd = self.components
#       self._log.info(Fore.CYAN + 'error={:6.3f};'.format(error) \
#               + Fore.MAGENTA + '\tKD={:8.5f};'.format(kd) \
#               + Fore.CYAN + Style.BRIGHT + '\tP={:8.5f}; I={:8.5f}; D={:8.5f}; setpoint={:6.3f};'.format(cp, ci, cd, self._setpoint) \
#               + Style.DIM + ' output: {:>6.3f};'.format(output))

        # keep track of state
        self._last_output = output
        self._last_input = target
        self._last_time = _now

        return output

    # ..........................................................................
    @property
    def sample_time(self):
        '''
           Return the sample time as a property.
        '''
        return self._sample_time

    # ..........................................................................
    @property
    def constants(self):
        '''
           The P-, I- and D- fixed terms, as a tuple.
        '''
        return self.kp, self.ki, self.kd

    # ..........................................................................
    @property
    def components(self):
        '''
           The P-, I- and D-terms from the last computation as separate
           components as a tuple. Useful for visualizing what the controller
           is doing or when tuning hard-to-tune systems.
        '''
        return self._proportional, self._integral, self._derivative

    # ..........................................................................
    @property
    def tunings(self):
        '''
           The tunings used by the controller as a tuple: (Kp, Ki, Kd)
        '''
        return self.kp, self.ki, self.kd

    # ..........................................................................
    @tunings.setter
    def tunings(self, tunings):
        '''
           Setter for the PID tunings.
        '''
        self._kp, self._ki, self._kd = tunings

    # ..........................................................................
    @property
    def output_limits(self):
        '''
           The curre_pom output limits as a 2-tuple: (lower, upper). See also
           the *output_limts* parameter in :meth:`PID.__init__`.
        '''
        return self._min_output, self._max_output

    # ..........................................................................
    @output_limits.setter
    def output_limits(self, limits):
        '''
           Setter for the output limits.
        '''
        if limits is None:
            self._min_output, self._max_output = None, None
            return
        min_output, max_output = limits
        if None not in limits and max_output < min_output:
            raise ValueError('lower limit must be less than upper limit')
        self._min_output  = min_output
        self._max_output  = max_output
        self._integral    = self.clamp(self._integral)
        self._last_output = self.clamp(self._last_output)

    # ..........................................................................
    def reset(self):
        '''
           Reset the PID controller internals, setting each term to 0 as well
           as cleaning the integral, the last output and the last input
           (derivative calculation).
        '''
        self._proportional = 0.0
        self._integral     = 0.0
        self._derivative   = 0.0
        self._last_time    = self._current_time()
        self._last_output  = None
        self._last_input   = None

    # ..........................................................................
    def clamp(self, value):
        '''
            Clamp the value between the lower and upper limits.
        '''
        if value is None:
            return None
        elif self._max_output is not None and value > self._max_output:
            return self._max_output
        elif self._min_output is not None and value < self._min_output:
            return self._min_output
        else:
            return value

# ==============================================================================
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
           :param config:  The application configuration, read from a YAML file.
           :param motor:        The motor to be controlled.
           :param setpoint: The initial setpoint or target output
           :param sample_time: The time in seconds before generating a new 
               output value. This PID is expected to be called at a constant
               rate.
           :param level: The log level, e.g., Level.INFO.
        '''
        if motor is None:
            raise ValueError('null motor argument.')
        self._motor = motor
        self._log = Logger('pidc:{}'.format(motor.orientation.label), level)
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

#       Velocity.CONFIG.configure(_config)

        self._enable_slew = _config.get('enable_slew')
        self._slewlimiter = SlewLimiter(config, orientation=self._motor.orientation, level=Level.INFO)
        _slew_rate = SlewRate.NORMAL # TODO _config.get('slew_rate')
        self._slewlimiter.set_rate_limit(_slew_rate)

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
    def reset(self):
        self._pid.velocity = 0.0
        self._pid.reset()
#       self._motor.reset_steps()
        self._motor.stop()
        self._log.info(Fore.GREEN + 'reset.')

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
        self._log.info(Fore.YELLOW + 'max velocity: {:5.2f}'.format(max_velocity))
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
    def _loop(self):
        '''
           The PID loop that continues while the enabled flag is True.
        '''
        _doc = Documentation.NONE
        _power_color = Fore.BLACK
        _lim = 0.2
        _last_velocity = 0.0
        _counter = itertools.count()

        if self._enable_slew:
            if not self._slewlimiter.is_enabled():
                self._log.info('slew enabled.')
                self._slewlimiter.enable()
        else:
            self._log.info('slew disabled.')
        while self._enabled:
            _count = next(_counter)
            _current_power = self._motor.get_current_power_level()
            _current_velocity = self._motor.velocity
            _vpr = round( _current_velocity / _current_power ) if _current_power > 0 else -1.0
            if self._pot_ctrl:
                _pot_value = self._pot.get_scaled_value()
                self._pid.kd = _pot_value
                self._log.debug('pot: {:8.5f}.'.format(_pot_value))
            if _vpr < 0.0:
                self._failures += 1
            elif self._failures > 0:
                self._failures -= 1
            self._power += self._pid(_current_velocity) #/ 100.0
            self._motor.set_motor_power(self._power / 100.0)

            if _doc is Documentation.MINIMAL:
                self._log.info('velocity: {:>5.2f}\t{:<5.2f}'.format(_current_velocity, self._pid.setpoint) + Style.RESET_ALL)

            elif _doc is Documentation.SIMPLE:
                if ( _last_velocity * 0.97 ) <= _current_velocity <= ( _last_velocity * 1.03 ): # within 3%
                    _velocity_color = Fore.YELLOW + Style.NORMAL
                elif _last_velocity < _current_velocity:
                    _velocity_color = Fore.MAGENTA + Style.NORMAL
                elif _last_velocity > _current_velocity:
                    _velocity_color = Fore.CYAN + Style.NORMAL
                else:
                    _velocity_color = Fore.BLACK 
                self._log.info('velocity:\t' + _velocity_color + '{:>5.2f}\t{:<5.2f}'.format(_current_velocity, self._pid.setpoint) + Style.RESET_ALL)

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

                kp, ki, kd = self._pid.constants
                cp, ci, cd = self._pid.components
                self._log.info(Fore.BLUE + 'cp={:7.4f}|ci={:7.4f}|cd={:7.4f}'.format(cp, ci, cd)\
                        + Fore.CYAN + '|kd={:<7.4f} '.format(kd) \
                        + _power_color + '\tpwr: {:>5.2f}/{:<5.2f}'.format(_current_power, self._power)\
                        + _velocity_color + '\tvel: {:>5.2f}/{:<5.2f}'.format(_current_velocity, self._pid.setpoint)\
#                       + Fore.CYAN + Style.NORMAL + ' \tvp ratio: {:>5.2f}%; {:d} fails;'.format(_vpr, self._failures)\
                        + Style.RESET_ALL)
#                       + '\t{:d}/{:d} steps.'.format(_diff_steps, self._max_diff_steps) + Style.RESET_ALL)

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
    @property
    def enabled(self):
        return self._enabled

    # ..........................................................................
    def enable(self):
        if not self._closed:
            self._log.info('enabling PID loop...')
            self._enabled = True
            # if we haven't started the thread yet, do so now...
            if self._thread is None:
                self._thread = threading.Thread(target=PIDController._loop, args=[self])
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
        self._disabling = True
        self._enabled = False
        time.sleep(0.06) # just a bit more than 1 loop in 20Hz
        if self._thread is not None:
            self._thread.join(timeout=1.0)
            self._log.debug('pid thread joined.')
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

#EOF
