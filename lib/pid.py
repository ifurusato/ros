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
# This class and the PIDController class were derived from ideas gleaned
# from libraries by both Martin Lundberg and Brett Beauregard, as well as
# helpful discussions with David Anderson of the DPRG.
#

import numpy, time
from colorama import init, Fore, Style
init()

from lib.logger import Logger, Level
from lib.enums import Orientation

# ..............................................................................
class PID(object):
    '''
    The PID controller itself.

    Note that the setpoint of this PID controller is a velocity setting;
    this is not to be confused with the velocity property of the motors.
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
        self._setpoint_limit = None
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
    def setpoint(self):
        '''
        The setpoint used by the controller as a tuple: (Kp, Ki, Kd)
        If a setpoint limit has been set the returned value is
        limited by the set value.
        '''
        return self._setpoint

    @setpoint.setter
    def setpoint(self, setpoint):
        '''
        Setter for the set point. If setpoint limit has been set and the
        argument exceeds the limit, the value is set to the setpoint limit.
        '''
        if self._setpoint_limit:
            if setpoint > self._setpoint_limit:
                self._setpoint = self._setpoint_limit
            elif setpoint < -1.0 * self._setpoint_limit:
                self._setpoint = -1.0 * self._setpoint_limit
            else:
                self._setpoint = setpoint
#           self._log.debug(Fore.RED + Style.BRIGHT + 'set setpoint: {:5.2f}; limited to: {:5.2f} from max vel: {:5.2f}'.format(setpoint, self._setpoint, self._setpoint_limit))
        else:
            self._setpoint = setpoint
#       if self._setpoint == 0.0:
#           self.reset()
#           self._log.debug(Fore.BLACK + 'set setpoint: {:5.2f}'.format(setpoint))

    # ..........................................................................
    def set_limit(self, limit):
        '''
        Setter for the setpoint limit. Set to None (the default) to
        disable this feature. Note that this doesn't affect the setting
        of the setpoint but rather the getting of the setpoint.
        '''
        if limit == None:
            self._log.info(Fore.CYAN + Style.DIM + 'setpoint limit: disabled')
        else:
            self._log.info(Fore.CYAN + 'setpoint limit: {:5.2f}'.format(limit))
        self._setpoint_limit = limit

    # ..........................................................................
    def __call__(self, target, dt=None):
        '''
        Call the PID controller with *target* and calculate and return a
        control output if sample_time seconds has passed since the last
        update. If no new output is calculated, return the previous output
        instead (or None if no value has been calculated yet).

        :param dt: If set, uses this value for timestep instead of real time.
                   This can be used in simulations when simulation time is
                   different from real time.
        '''
        _now = self._current_time()
        if dt is None:
            dt = _now - self._last_time
#           dt = _now - self._last_time if _now - self._last_time else 1e-16
            self._log.info(Fore.BLUE + '__call__  dt: {:7.4f}'.format(dt) + Style.RESET_ALL)
        elif dt <= 0:
            raise ValueError("dt has nonpositive value {}. Must be positive.".format(dt))

        if dt < self._sample_time and self._last_output is not None:
            # only update every sample_time seconds
            self._log.info(Fore.RED + '__call__() last output: {:5.2f}'.format(self._last_output) + Style.RESET_ALL)
            return self._last_output

        # compute error terms
        _error = self.setpoint - target
        d_input = target - (self._last_input if self._last_input is not None else target)

        # compute the proportional, integral and derivative terms
        self._proportional = self.kp * _error
        self._integral    += self.ki * _error * dt
        self._integral     = self.clamp(self._integral)  # avoid integral windup
        self._derivative   = -self.kd * d_input / dt

        # compute output
        output = self.clamp(self._proportional + self._integral + self._derivative)

        kp, ki, kd = self.constants
        cp, ci, cd = self.components
#       self._log.info(Fore.CYAN + 'target={:5.2f}; error={:6.3f};'.format(target, _error) \
#               + Fore.MAGENTA + '\tKD={:8.5f};'.format(kd) \
#               + Fore.CYAN + Style.BRIGHT + '\tP={:8.5f}; I={:8.5f}; D={:8.5f}; setpoint={:6.3f};'.format(cp, ci, cd, self._setpoint) \
#               + Style.DIM + ' output: {:>6.3f}'.format(output))

        # keep track of state
        self._last_output = output
        self._last_input  = target
        self._last_time   = _now
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
        The output limits as a 2-tuple: (lower, upper). See also
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
    def print_state(self):
        _fore = Fore.RED if self._orientation == Orientation.PORT else Fore.GREEN
        self._log.info(_fore + 'kp:             \t{}'.format(self.kp))
        self._log.info(_fore + 'ki:             \t{}'.format(self.ki))
        self._log.info(_fore + 'kd:             \t{}'.format(self.kd))

        self._log.info(_fore + 'min_output:     \t{}'.format(self._min_output))
        self._log.info(_fore + 'max_output:     \t{}'.format(self._max_output))
        self._log.info(_fore + 'setpoint:       \t{}'.format(self._setpoint))
        self._log.info(_fore + 'setpoint limit: \t{}'.format(self._setpoint_limit))
        self._log.info(_fore + 'sample_time:    \t{}'.format(self._sample_time))

        self._log.info(_fore + 'proportional:   \t{}'.format(self._proportional))
        self._log.info(_fore + 'integral:       \t{}'.format(self._integral))
        self._log.info(_fore + 'derivative:     \t{}'.format(self._derivative))
        self._log.info(_fore + 'last_output:    \t{}'.format(self._last_output))
        self._log.info(_fore + 'last_input:     \t{}'.format(self._last_input))
        self._log.info(_fore + 'last_time:      \t{}'.format(self._last_time))

    # ..........................................................................
    def reset(self):
        '''
        Reset the PID controller internals, setting each term to 0 as well
        as cleaning the integral, the last output and the last input
        (derivative calculation).

        Note that after the setpoint has been set to zero if the motors
        have been running the last input and output values remain at 
        their previous values. This storing of previous state causes 
        problems when starting up again. The reset() function cleans 
        any stored state.
        '''
        self._log.info(Fore.YELLOW + 'reset ========================= ')
        self.setpoint      = 0.0
        self._proportional = 0.0
        self._integral     = 0.0
        self._derivative   = 0.0
        self._last_output  = 0.0
        self._last_input   = 0.0
        self._last_time    = self._current_time()

    # ..........................................................................
    def clamp(self, value):
        '''
        Clamp the value between the lower and upper limits.
        '''
        return numpy.clip(value, self._min_output, self._max_output)

#EOF
