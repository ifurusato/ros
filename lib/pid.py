#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# Copyright 2020 by Murray Altheim. All rights reserved. This file is part of
# the Robot OS project and is released under the "Apache Licence, Version 2.0".
# Please see the LICENSE file included as part of this package.
#
# author:   Murray Altheim
# created:  2020-04-20
# modified: 2020-04-21
#

import sys, time, itertools
from collections import deque
from colorama import init, Fore, Style
init()

try:
    import numpy
except ImportError:
    exit("This script requires the numpy module\nInstall with: sudo pip install numpy")

from lib.logger import Level, Logger
from lib.enums import Direction, Orientation, SlewRate, Speed, Velocity
from lib.filewriter import FileWriter
from lib.slewlimiter import SlewLimiter

# _current_power = lambda: _motor.get_current_power_level()
# _set_power = lambda p: _motor.set_motor_power(p)

# ..............................................................................
class PID():
    '''
        A PID controller seeks to keep some input variable close to a desired
        setpoint by adjusting an output. The way in which it does this can be
        'tuned' by adjusting three parameters (P,I,D).

        If a FileWriter is set odometry data will be written to a data file.

        This uses the ros:motors:pid: section of the YAML configuration.
    '''
    def __init__(self, config, motor, level):
        self._motor = motor
        self._orientation = motor.get_orientation()
        self._log = Logger('pid:{}'.format(self._orientation.label), level)

        self._millis  = lambda: int(round(time.time() * 1000))
        self._counter = itertools.count()
        self._last_error = 0.0
        self._sum_errors = 0.0
        self._filewriter = None              # optional: for statistics
        self._stats_queue = None
        self._filewriter_closed = False

        # PID configuration ..........................................
        cfg = config['ros'].get('motors').get('pid')
        self._enable_slew = cfg.get('enable_slew')
        if self._enable_slew:
            # slew limiter ...............................................
            self._slewlimiter = SlewLimiter(config, self._orientation, Level.INFO)

        _clip_max = cfg.get('clip_limit')
        _clip_min = -1.0 * _clip_max
        self._clip   = lambda n: _clip_min if n <= _clip_min else _clip_max if n >= _clip_max else n
        self._enable_p = cfg.get('enable_p')
        self._enable_i = cfg.get('enable_i')
        self._enable_d = cfg.get('enable_d')
        _kp = cfg.get('kp')
        _ki = cfg.get('ki')
        _kd = cfg.get('kd')
        self.set_tuning(_kp, _ki, _kd)
        self._sample_time_ms = cfg.get('sample_time_ms') # default sample time is 20ms
        self._sample_time_s = self._sample_time_ms / 1000
        self._last_time = self._millis() - self._sample_time_ms
        self._log.info('ready.')

    # ..............................................................................
    def set_filewriter(self, filewriter):
        '''
            If a FileWriter is set then the Motor will generate odometry data
            and write this to a data file whose directory and filename are
            determined by configuration.
        '''
        self._filewriter = filewriter
        if self._filewriter:
            if self._stats_queue is None:
                self._stats_queue = deque()
            self._filewriter.enable(self._stats_queue)
            self._log.info('filewriter enabled.')

    # ..........................................................................
    def get_tuning(self):
        return [ self._kp, self._ki, self._kd ]

    # ..........................................................................
    def get_tuning_info(self):
        '''
           Returns the tuning information, formatted and including if the
           setting is enabled or disabled.
        '''
        _en_p = 'on' if self._enable_p else 'off'
        _en_i = 'on' if self._enable_i else 'off'
        _en_d = 'on' if self._enable_d else 'off'
        return [ '{:d}'.format(self._elapsed_sec),\
                 '{:6.4f} ({})'.format(self._kp, _en_p),\
                 '{:6.4f} ({})'.format(self._ki, _en_i),\
                 '{:6.4f} ({})'.format(self._kd, _en_d) ]

    # ..........................................................................
    def set_tuning(self, p, i, d):
        '''
            Set the tuning of the power PID controller.
        '''
        self._kp = p
        self._ki = i
        self._kd = d
        self._log.info('set PID tuning; P={:>5.2f}; I={:>5.2f}; D={:>5.2f}.'.format(self._kp, self._ki, self._kd))

    # ..........................................................................
    def step_to(self, target_velocity, direction, slew_rate, steps, f_is_enabled):
        '''
            Performs the PID calculation during a loop, returning once the
            number of steps have been reached.

            Velocity is the target velocity of the robot, expressed as
            either an enumerated value or a decimal from 0.0 to 100.0,
            where 50.0 is considered half-speed (though this will not be
            true in practice, until we tune these values).
        '''
        _current_steps = self._motor.get_steps() # current steps

        if type(target_velocity) is Velocity:
            _target_velocity = target_velocity.value
        else:
            _target_velocity = target_velocity

        _step_limit = _current_steps + steps

        self._start_time = time.time()
        _is_accelerating = (self._motor.get_velocity() < _target_velocity)

        self._direction = direction
        if direction is Direction.REVERSE:
            _target_velocity = -1.0 * _target_velocity

        if self._enable_slew:
            if not self._slewlimiter.is_enabled():
                self._slewlimiter.enable()
                self._slewlimiter.start()

        while f_is_enabled() and (( direction is Direction.FORWARD and self._motor.get_steps() < _step_limit ) or \
              ( direction is Direction.REVERSE and self._motor.get_steps() > _step_limit )):
            if self._enable_slew:
                _slewed_target_velocity = self._slewlimiter.slew(self._motor.get_velocity(), _target_velocity)
                _changed = self._compute(_slewed_target_velocity)
            else:
                _changed = self._compute(_target_velocity)

            self._log.debug(Fore.BLACK + Style.DIM + '{:d}/{:d} steps.'.format(self._motor.get_steps(), _step_limit))
            if not _changed and self._motor.get_velocity() == 0.0 and _target_velocity == 0.0 and _step_limit > 0: # we will never get there if we aren't moving
                break

            # info only:
            if _is_accelerating and self._motor.get_velocity() >= _target_velocity:
                _elapsed = time.time() - self._start_time
                _is_accelerating = False
                self._log.info(Fore.GREEN + Style.BRIGHT + 'reached target velocity of {:+06.2f} at {:5.2f} sec elapsed.'.format(_target_velocity, _elapsed))

            if self._motor.is_interrupted():
                break
            time.sleep(self._sample_time_s) # 20ms

        _elapsed = time.time() - self._start_time
        self._elapsed_sec = int(round(_elapsed)) + 1
        self._log.info(Fore.GREEN + Style.BRIGHT + 'step to complete; {:5.2f} sec elapsed.'.format(_elapsed))
        if self._enable_slew: # if not a repeat call
            self._slewlimiter.reset(0.0)
        self._motor.reset_interrupt()

    # ..........................................................................
    def _compute(self, target_velocity):
        '''
            The PID power compute function, called upon each loop.

            Returns True if PID computed a change, False if the error was zero and no change was applied.
        '''
        _now = self._millis()
        _time_change = _now - self._last_time
        if _time_change >= self._sample_time_ms:
            self._loop_count = next(self._counter)

            # compare current and target velocities ............................
            _current_velocity = self._motor.get_velocity()
            _error = target_velocity - _current_velocity
#           if _current_velocity == 0:
#               self._log.debug(Fore.CYAN + Style.NORMAL + '[{:0d}]; velocity: {:+06.2f} ➔ {:+06.2f}\t _error: {:>5.2f}.'.format(self._loop_count, _current_velocity, target_velocity, _error))
#           else:
#               self._log.debug(Fore.CYAN + Style.BRIGHT + '[{:0d}]; velocity: {:+06.2f} ➔ {:+06.2f}\t _error: {:>5.2f}.'.format(self._loop_count, _current_velocity, target_velocity, _error))
            _current_power = self._motor.get_current_power_level() * ( 1.0 / self._motor.get_max_power_ratio() )
            _power_level = _current_power

            if PID.equals_zero(_error):

                if target_velocity == 0.0:
                    self._motor.set_motor_power(0.0)
                    self._log.info(Fore.WHITE + Style.BRIGHT + '[{:02d}]+ NO ERROR, currently at zero velocity.'.format(self._loop_count))
                else:
                    self._log.info(Fore.WHITE + Style.BRIGHT + '[{:02d}]+ no error, currently at target velocity:  {:+06.2f}; at power: {:+5.3f}'.format(self._loop_count, _current_velocity, _current_power))
                # remember some variables for next time ........................
                self._last_error = 0.0
                _changed = False

            else:

                # P: Proportional ..............................................
                if self._enable_p:
                    _p_diff = self._kp * _error
                    self._log.debug(Fore.BLUE + Style.BRIGHT + 'P diff: {:>5.4f}'.format(_p_diff) + Style.NORMAL + ' = self._kp: {:>5.4f} * _error: {:>5.4f}.'.format(self._kp, _error))
                else:
                    _p_diff = 0.0

                # I: Integral ..................................................
                if self._enable_i:
                    _i_diff = self._ki * self._sum_errors if self._enable_i else 0.0
                    self._log.debug(Fore.MAGENTA + Style.BRIGHT + 'I diff: {:45.4f}'.format(_i_diff) + Style.NORMAL + ' = self._ki: {:>5.4f} * _sum_errors: {:>5.4f}.'.format(self._ki, self._sum_errors))
                else:
                    _i_diff = 0.0

                # D: Derivative ................................................
                if self._enable_d:
                    _d_diff = self._kd * self._last_error if self._enable_d else 0.0
                    self._log.debug(Fore.YELLOW              + 'D diff: {:>5.4f}'.format(_d_diff) + Style.NORMAL + ' = self._kd: {:>5.4f} * _last_error: {:>5.4f}.'.format(self._kd, self._last_error))
                else:
                    _d_diff = 0.0

                # calculate output .............................................
                _output = _p_diff + _i_diff + _d_diff
    #           self._log.debug(Fore.CYAN + Style.BRIGHT + '_output: {:>5.4f}'.format(_output) + Style.NORMAL + ' = (P={:+5.4f}) + (I={:+5.4f}) + (D={:+5.4f})'.format(_p_diff, _i_diff, _d_diff))

                # clipping .....................................................
                _clipped_output = self._clip(_output)

                # set motor power ..............................................
                _power_level = _current_power + _clipped_output
                if abs(_output) <= 0.0005: # we're pretty close to the right value
                    self._log.debug(Fore.WHITE + Style.NORMAL + '[{:02d}]+ velocity:  {:+06.2f} ➔ {:+06.2f}'.format(self._loop_count, _current_velocity, target_velocity) + Style.BRIGHT + '\t new power: {:+5.3f}'.format(_power_level)\
                            + Style.NORMAL + ' = current: {:+5.3f} + output: {:+5.3f}   '.format(_current_power, _clipped_output) + Style.DIM + '\tP={:+5.4f}\tI={:+5.4f}\tD={:+5.4f}'.format(_p_diff, _i_diff, _d_diff))
                elif _output >= 0: # we're going too slow
                    self._log.debug(Fore.GREEN + Style.NORMAL + '[{:02d}]+ velocity:  {:+06.2f} ➔ {:+06.2f}'.format(self._loop_count, _current_velocity, target_velocity) + Style.BRIGHT + '\t new power: {:+5.3f}'.format(_power_level)\
                            + Style.NORMAL + ' = current: {:+5.3f} + output: {:+5.3f}   '.format(_current_power, _clipped_output) + Style.DIM + '\tP={:+5.4f}\tI={:+5.4f}\tD={:+5.4f}'.format(_p_diff, _i_diff, _d_diff))
                else:              # we're going too fast
                    self._log.debug(Fore.RED   + Style.NORMAL + '[{:02d}]+ velocity:  {:+06.2f} ➔ {:+06.2f}'.format(self._loop_count, _current_velocity, target_velocity) + Style.BRIGHT + '\t new power: {:+5.3f}'.format(_power_level)\
                            + Style.NORMAL + ' = current: {:+5.3f} + output: {:+5.3f}   '.format(_current_power, _clipped_output) + Style.DIM + '\tP={:+5.4f}\tI={:+5.4f}\tD={:+5.4f}'.format(_p_diff, _i_diff, _d_diff))

                self._motor.set_motor_power(_power_level)

                # remember some variables for next time ........................
                self._last_error = _error
                self._sum_errors += _error
                _changed = True

            # if configured, capture odometry data ...................
            if self._filewriter:
                _elapsed = time.time() - self._start_time
                _data = '{:>5.3f}\t{:>5.2f}\t{:>5.2f}\t{:>5.2f}\t{:d}\n'.format(_elapsed, ( _power_level * 100.0), _current_velocity, target_velocity, self._motor.get_steps())
                self._stats_queue.append(_data)
                self._log.debug('odometry:' + Fore.BLACK + ' time: {:>5.3f};\tpower: {:>5.2f};\tvelocity: {:>5.2f}/{:>5.2f}\tsteps: {:d}'.format(\
                        _elapsed, _power_level, _current_velocity, target_velocity, self._motor.get_steps()))

            self._last_time = _now
            return _changed

    # ..........................................................................
    @staticmethod
    def equals_zero(value):
        '''
            Returns True if the value is within 2% of 0.0.
        '''
#       return value == 0.0
        return numpy.isclose(value, 0.0, rtol=0.02, atol=0.0)

    # ..........................................................................
    def enable(self):
        self._log.info('{} enabled.'.format(self._orientation))
        pass

    # ..........................................................................
    def disable(self):
        self._log.info('{} disabled.'.format(self._orientation))
        pass

    # ..........................................................................
    def close_filewriter(self):
        if not self._filewriter_closed:
            self._filewriter_closed = True
            if self._filewriter:
                _tuning = self.get_tuning_info()
                self._filewriter.write_gnuplot_settings(_tuning)
                self._filewriter.disable()

    # ..........................................................................
    def close(self):
        self.close_filewriter()
        self._log.info('closed.')


#EOF
