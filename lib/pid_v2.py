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

import sys, time, itertools, math
from collections import deque
from colorama import init, Fore, Style
init()

try:
    import numpy
except ImportError:
    exit("This script requires the numpy module\nInstall with: sudo pip install numpy")

from lib.logger import Level, Logger
from lib.enums import Direction, Orientation, Speed, Velocity
from lib.filewriter import FileWriter
from lib.slew import SlewRate, SlewLimiter
from lib.rate import Rate

# _current_power = lambda: _motor.get_current_power_level()
# _set_power = lambda p: _motor.set_motor_power(p)

# ..............................................................................
class PID():
    '''
        A PID controller seeks to keep some input variable close to a desired
        setpoint by adjusting an output. The way in which it does this can be
        'tuned' by adjusting three parameters (P,I,D).

        This uses the ros:motors:pid: and ros:geometry: sections of the
        YAML configuration.

        If a FileWriter is set odometry data will be written to a data file.

        Various formulae are found at the bottom of this file.
    '''
    def __init__(self, config, motor, level):
        self._motor = motor
        self._orientation = motor.get_orientation()
        self._log = Logger('pid:{}'.format(self._orientation.label), level)

        # PID configuration ................................
        if config is None:
            raise ValueError('null configuration argument.')
        _config = config['ros'].get('motors').get('pid')
        self._enable_slew = _config.get('enable_slew')
        if self._enable_slew:
            self._slewlimiter = SlewLimiter(config, self._orientation, Level.INFO)
        # geometry configuration ...........................
        _geo_config = config['ros'].get('geometry')
        self._wheel_diameter = _geo_config.get('wheel_diameter')
        self._wheelbase      = _geo_config.get('wheelbase')
        self._step_per_rotation = _geo_config.get('steps_per_rotation')

        _clip_max = _config.get('clip_limit')
        _clip_min = -1.0 * _clip_max
        self._clip   = lambda n: _clip_min if n <= _clip_min else _clip_max if n >= _clip_max else n
        self._enable_p = _config.get('enable_p')
        self._enable_i = _config.get('enable_i')
        self._enable_d = _config.get('enable_d')
        _kp = _config.get('kp')
        _ki = _config.get('ki')
        _kd = _config.get('kd')
        self.set_tuning(_kp, _ki, _kd)
        self._rate = Rate(_config.get('sample_freq_hz')) # default sample rate is 20Hz
#       self._millis  = lambda: int(round(time.time() * 1000))
        self._counter = itertools.count()
        self._last_error = 0.0
        self._sum_errors = 0.0
        self._step_limit = 0
        self._stats_queue = None
        self._filewriter = None  # optional: for statistics
        self._filewriter_closed = False

        _wheel_circumference = math.pi * self._wheel_diameter # mm
        self._steps_per_m  = 1000.0 * self._step_per_rotation  / _wheel_circumference 
        self._log.info( Fore.BLUE + Style.BRIGHT + '{:5.2f} steps per m.'.format(self._steps_per_m))
        self._steps_per_cm = 10.0 * self._step_per_rotation  / _wheel_circumference 
        self._log.info( Fore.BLUE + Style.BRIGHT + '{:5.2f} steps per cm.'.format(self._steps_per_cm))

        self._log.info('ready.')

    # ..........................................................................
    def set_tuning(self, p, i, d):
        '''
            Set the tuning of the power PID controller.
        '''
        self._kp = p
        self._ki = i
        self._kd = d
        self._log.info('set PID tuning for {} motor: P={:>8.5f}; I={:>8.5f}; D={:>8.5f}.'.format(self._orientation.name, self._kp, self._ki, self._kd))

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

    # ..............................................................................
    def get_steps(self):
        '''
           A convenience method that returns the number of steps registered by the motor encoder.
        '''
        return self._motor.get_steps()

    # ..........................................................................
    def is_stepping(self, direction):
        '''
            Returns True if the motor step count is less than the currently-set 
            step limit, or if traveling in REVERSE, greater than the step limit.
        '''
#       while f_is_enabled() and (( direction is Direction.FORWARD and self.get_steps() < _step_limit ) or \
#                                 ( direction is Direction.REVERSE and self.get_steps() > _step_limit )):
#       return ( self.get_steps() < self._step_limit ) if direction is Direction.FORWARD else ( self.get_steps() > self._step_limit )
        if direction is Direction.FORWARD:
            self._log.debug(Fore.MAGENTA + '{} is stepping forward? {:>5.2f} < {:>5.2f}'.format(self._orientation, self.get_steps(), self._step_limit ))
            return ( self.get_steps() < self._step_limit )
        elif direction is Direction.REVERSE:
            self._log.debug(Fore.MAGENTA + '{} is stepping reverse? {:>5.2f} > {:>5.2f}'.format(self._orientation, self.get_steps(), self._step_limit ))
            return ( self.get_steps() > self._step_limit )
        else:
            raise Exception('no direction provided.')

    # ..........................................................................
    def set_step_limit(self, direction, steps):
        '''
            Sets the step limit (i.e., the goal) prior to a call to step_to().
        '''
        if direction is Direction.FORWARD:
            self._step_limit = self.get_steps() + steps
        elif direction is Direction.REVERSE:
            self._step_limit = self.get_steps() - steps
        else:
            raise Exception('no direction provided.')

    # ..........................................................................
    def set_velocity(self, velocity):
        '''
            Sets the velocity of the motor to the specified Velocity.
        '''
        if type(target_velocity) is not Velocity:
            raise Exception('expected Velocity argument, not {}'.format(type(target_velocity)))
        _target_velocity = target_velocity.value

        self._start_time = time.time()

        if direction is Direction.FORWARD: # .......................................................

            self._log.info(Fore.GREEN + Style.BRIGHT + 'current velocity: {};'.format(self._motor.get_velocity()) \
                    + Fore.CYAN + Style.NORMAL + ' target velocity: {}; step limit: {}.'.format(_target_velocity, self._step_limit))

            while f_is_enabled() and self.is_stepping(direction): # or ( direction is Direction.REVERSE and self.get_steps() > self._step_limit )):
                _changed = self._compute(_target_velocity)
    
                self._log.debug(Fore.BLACK + Style.DIM + '{:d}/{:d} steps.'.format(self.get_steps(), self._step_limit))
                if not _changed and self._motor.get_velocity() == 0.0 and _target_velocity == 0.0 and self._step_limit > 0: # we will never get there if we aren't moving
                    self._log.info(Fore.RED + 'break 2.')
                    break
    
                self._rate.wait() # 20Hz

                if self._motor.is_interrupted():
                    self._log.info(Fore.RED + 'motor interrupted.')
                    break

                if self._orientation is Orientation.PORT:
                    self._log.info(Fore.RED + 'current velocity: {:>5.2f};'.format(self._motor.get_velocity() ) \
                            + Fore.CYAN + ' target velocity: {}; {:d} steps of: {}.'.format(_target_velocity, self.get_steps(), self._step_limit))
                else:
                    self._log.info(Fore.GREEN + 'current velocity: {:>5.2f};'.format(self._motor.get_velocity() ) \
                            + Fore.CYAN + ' target velocity: {}; {:d} steps of: {}.'.format(_target_velocity, self.get_steps(), self._step_limit))

        elif direction is Direction.REVERSE: # .....................................................

            _target_velocity = -1.0 * _target_velocity

            self._log.info(Fore.RED + Style.BRIGHT + 'target velocity: {}; step limit: {}.'.format(_target_velocity, self._step_limit))

            while f_is_enabled() and self.is_stepping(direction): # or ( direction is Direction.REVERSE and self.get_steps() > self._step_limit )):
                _changed = self._compute(_target_velocity)
                self._log.debug(Fore.BLACK + Style.DIM + '{:d}/{:d} steps.'.format(self.get_steps(), self._step_limit))
                if not _changed and self._motor.get_velocity() == 0.0 and _target_velocity == 0.0 and self._step_limit > 0: # we will never get there if we aren't moving
                    break
    

                if self._motor.is_interrupted():
                    break

        else: # ....................................................................................
            raise Exception('no direction provided.')

        self._rate.wait() # 20Hz
        # ======================================================================


    # ..........................................................................
    def step_to(self, target_velocity, direction, slew_rate, f_is_enabled):
        '''
            Performs the PID calculation during a loop, returning once the
            number of steps have been reached.

            Velocity is the target velocity of the robot, expressed as
            either an enumerated value or a decimal from 0.0 to 100.0,
            where 50.0 is considered half-speed (though this will not be
            true in practice, until we tune these values).
        '''

        if type(target_velocity) is not Velocity:
            raise Exception('expected Velocity argument, not {}'.format(type(target_velocity)))
        _target_velocity = target_velocity.value

        self._start_time = time.time()

        if self._enable_slew:
            if not self._slewlimiter.is_enabled():
                print(Fore.GREEN + 'slew enabled.' + Style.RESET_ALL)
                self._slewlimiter.set_rate_limit(slew_rate)
                self._slewlimiter.enable()
                self._slewlimiter.start()
        else:
            print(Fore.GREEN + 'slew disabled; f_is_enabled? {}'.format(f_is_enabled()) + Style.RESET_ALL)

        if direction is Direction.FORWARD: # .......................................................

            _is_accelerating = self._motor.get_velocity() < _target_velocity
            self._log.info(Fore.GREEN + Style.BRIGHT + 'current velocity: {};'.format(self._motor.get_velocity()) \
                    + Fore.CYAN + Style.NORMAL + ' target velocity: {}; step limit: {}; is_accelerating: {}.'.format(_target_velocity, self._step_limit, _is_accelerating))

            while f_is_enabled() and self.is_stepping(direction): # or ( direction is Direction.REVERSE and self.get_steps() > self._step_limit )):
                if self._enable_slew:
                    _slewed_target_velocity = self._slewlimiter.slew(self._motor.get_velocity(), _target_velocity)
                    _changed = self._compute(_slewed_target_velocity)
                else:
                    _changed = self._compute(_target_velocity)
    
                self._log.debug(Fore.BLACK + Style.DIM + '{:d}/{:d} steps.'.format(self.get_steps(), self._step_limit))
                if not _changed and self._motor.get_velocity() == 0.0 and _target_velocity == 0.0 and self._step_limit > 0: # we will never get there if we aren't moving
                    self._log.info(Fore.RED + 'break 2.')
                    break
    
                # displays info only:
                if _is_accelerating and self._motor.get_velocity() >= _target_velocity:
                    _elapsed = time.time() - self._start_time
                    _is_accelerating = False
                    self._log.info(Fore.GREEN + Style.BRIGHT + 'reached target velocity of {:+06.2f} at {:5.2f} sec elapsed.'.format(_target_velocity, _elapsed))
    
                self._rate.wait() # 20Hz

                if self._motor.is_interrupted():
                    self._log.info(Fore.RED + 'motor interrupted.')
                    break

                if self._orientation is Orientation.PORT:
                    self._log.info(Fore.RED + 'current velocity: {:>5.2f};'.format(self._motor.get_velocity() ) \
                            + Fore.CYAN + ' target velocity: {}; {:d} steps of: {}; is_accelerating: {}.'.format(_target_velocity, self.get_steps(), self._step_limit, _is_accelerating))
                else:
                    self._log.info(Fore.GREEN + 'current velocity: {:>5.2f};'.format(self._motor.get_velocity() ) \
                            + Fore.CYAN + ' target velocity: {}; {:d} steps of: {}; is_accelerating: {}.'.format(_target_velocity, self.get_steps(), self._step_limit, _is_accelerating))

        elif direction is Direction.REVERSE: # .....................................................

            _target_velocity = -1.0 * _target_velocity
            _is_accelerating = self._motor.get_velocity() < _target_velocity
            self._log.info(Fore.RED + Style.BRIGHT + 'target velocity: {}; step limit: {}; is_accelerating: {}.'.format(_target_velocity, self._step_limit, _is_accelerating))

            while f_is_enabled() and self.is_stepping(direction): # or ( direction is Direction.REVERSE and self.get_steps() > self._step_limit )):
                if self._enable_slew:
                    _slewed_target_velocity = self._slewlimiter.slew(self._motor.get_velocity(), _target_velocity)
                    _changed = self._compute(_slewed_target_velocity)
                else:
                    _changed = self._compute(_target_velocity)
    
                self._log.debug(Fore.BLACK + Style.DIM + '{:d}/{:d} steps.'.format(self.get_steps(), self._step_limit))
                if not _changed and self._motor.get_velocity() == 0.0 and _target_velocity == 0.0 and self._step_limit > 0: # we will never get there if we aren't moving
                    break
    
                # displays info only:
                if _is_accelerating and self._motor.get_velocity() >= _target_velocity:
                    _elapsed = time.time() - self._start_time
                    _is_accelerating = False
                    self._log.info(Fore.GREEN + Style.BRIGHT + 'reached target velocity of {:+06.2f} at {:5.2f} sec elapsed.'.format(_target_velocity, _elapsed))
    
                self._rate.wait() # 20Hz

                if self._motor.is_interrupted():
                    break

        else: # ....................................................................................
            raise Exception('no direction provided.')

        _elapsed = time.time() - self._start_time
        self._elapsed_sec = int(round(_elapsed)) + 1
        self._log.info('{} motor step-to complete; {:5.2f} sec elapsed;'.format(self._orientation.name, _elapsed) + Fore.MAGENTA + ' {:d}/{:d} steps.'.format(self.get_steps(), self._step_limit))
        if self._enable_slew: # if not a repeat call
            self._slewlimiter.reset(0.0)
        self._motor.reset_interrupt()

    # ..........................................................................
    def _compute(self, target_velocity):
        '''
            The PID power compute function, called upon each loop.

            Returns True if PID computed a change, False if the error was zero and no change was applied.
        '''
        self._loop_count = next(self._counter)

        # compare current and target velocities ............................
        _current_velocity = self._motor.get_velocity()
        _error = target_velocity - _current_velocity
#       if _current_velocity == 0:
#           self._log.debug(Fore.CYAN + Style.NORMAL + '[{:0d}]; velocity: {:+06.2f} ➔ {:+06.2f}\t _error: {:>5.2f}.'.format(self._loop_count, _current_velocity, target_velocity, _error))
#       else:
#           self._log.debug(Fore.CYAN + Style.BRIGHT + '[{:0d}]; velocity: {:+06.2f} ➔ {:+06.2f}\t _error: {:>5.2f}.'.format(self._loop_count, _current_velocity, target_velocity, _error))
        _current_power = self._motor.get_current_power_level() * ( 1.0 / self._motor.get_max_power_ratio() )
        _power_level = _current_power

        if PID.equals_zero(_error):

            if target_velocity == 0.0:
                self._motor.set_motor_power(0.0)
                self._log.info(Fore.WHITE + Style.BRIGHT + '[{:02d}]+ NO ERROR, currently at zero velocity.'.format(self._loop_count))
            else:
                self._log.info(Fore.WHITE + Style.BRIGHT + '[{:02d}]+ no error, currently at target velocity:  {:+06.2f}; at power: {:+5.3f}'.format(\
                        self._loop_count, _current_velocity, _current_power))
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
                self._log.debug(Fore.MAGENTA + Style.BRIGHT + 'I diff: {:45.4f}'.format(_i_diff) + Style.NORMAL \
                        + ' = self._ki: {:>5.4f} * _sum_errors: {:>5.4f}.'.format(self._ki, self._sum_errors))
            else:
                _i_diff = 0.0

            # D: Derivative ................................................
            if self._enable_d:
                _d_diff = self._kd * self._last_error if self._enable_d else 0.0
                self._log.debug(Fore.YELLOW + 'D diff: {:>5.4f}'.format(_d_diff) + Style.NORMAL + ' = self._kd: {:>5.4f} * _last_error: {:>5.4f}.'.format(self._kd, self._last_error))
            else:
                _d_diff = 0.0

            # calculate output .............................................
            _output = _p_diff + _i_diff + _d_diff
    #       self._log.debug(Fore.CYAN + Style.BRIGHT + '_output: {:>5.4f}'.format(_output) + Style.NORMAL + ' = (P={:+5.4f}) + (I={:+5.4f}) + (D={:+5.4f})'.format(_p_diff, _i_diff, _d_diff))

            # clipping .....................................................
            _clipped_output = self._clip(_output)

            # set motor power ..............................................
            _power_level = _current_power + _clipped_output
            if abs(_output) <= 0.0005: # we're pretty close to the right value
                self._log.debug(Fore.WHITE + Style.NORMAL + '[{:02d}]+ velocity:  {:+06.2f} ➔ {:+06.2f}'.format(self._loop_count, _current_velocity, target_velocity) \
                        + Style.BRIGHT + '\t new power: {:+5.3f}'.format(_power_level) + Style.NORMAL + ' = current: {:+5.3f} + output: {:+5.3f}   '.format(\
                        _current_power, _clipped_output) + Style.DIM + '\tP={:+5.4f}\tI={:+5.4f}\tD={:+5.4f}'.format(_p_diff, _i_diff, _d_diff))
            elif _output >= 0: # we're going too slow
                self._log.debug(Fore.GREEN + Style.NORMAL + '[{:02d}]+ velocity:  {:+06.2f} ➔ {:+06.2f}'.format(self._loop_count, _current_velocity, target_velocity) \
                        + Style.BRIGHT + '\t new power: {:+5.3f}'.format(_power_level) + Style.NORMAL + ' = current: {:+5.3f} + output: {:+5.3f}   '.format(\
                        _current_power, _clipped_output) + Style.DIM + '\tP={:+5.4f}\tI={:+5.4f}\tD={:+5.4f}'.format(_p_diff, _i_diff, _d_diff))
            else:              # we're going too fast
                self._log.debug(Fore.RED   + Style.NORMAL + '[{:02d}]+ velocity:  {:+06.2f} ➔ {:+06.2f}'.format(self._loop_count, _current_velocity, target_velocity) \
                        + Style.BRIGHT + '\t new power: {:+5.3f}'.format(_power_level) + Style.NORMAL + ' = current: {:+5.3f} + output: {:+5.3f}   '.format(\
                        _current_power, _clipped_output) + Style.DIM + '\tP={:+5.4f}\tI={:+5.4f}\tD={:+5.4f}'.format(_p_diff, _i_diff, _d_diff))

            self._motor.set_motor_power(_power_level)

            # remember some variables for next time ........................
            self._last_error = _error
            self._sum_errors += _error
            _changed = True

        # if configured, capture odometry data ...................
        if self._filewriter:
            _elapsed = time.time() - self._start_time
            _data = '{:>5.3f}\t{:>5.2f}\t{:>5.2f}\t{:>5.2f}\t{:d}\n'.format(_elapsed, ( _power_level * 100.0), _current_velocity, target_velocity, self.get_steps())
            self._stats_queue.append(_data)
            self._log.debug('odometry:' + Fore.BLACK + ' time: {:>5.3f};\tpower: {:>5.2f};\tvelocity: {:>5.2f}/{:>5.2f}\tsteps: {:d}'.format(\
                    _elapsed, _power_level, _current_velocity, target_velocity, self.get_steps()))

        return _changed

    # ..........................................................................
    def enable(self):
        if not self._closed:
            self._enabled = True
            # if we haven't started the thread yet, do so now...
            if self._thread is None:
                self._thread = threading.Thread(target=PID._loop, args=[self])
                self._thread.start()
                self._log.info('PID loop for {} motor enabled.'.format(self._orientation))
            else:
                self._log.warning('cannot enable PID loop for {} motor: thread already exists.'.format(self._orientation))
        else:
            self._log.warning('cannot enable PID loop for {} motor: already closed.'.format(self._orientation))

    # ..........................................................................
    def disable(self):
        self._enabled = False
        time.sleep(self._loop_delay_sec_div_10)
        if self._thread is not None:
            self._thread.join(timeout=1.0)
            self._log.debug('battery check thread joined.')
            self._thread = None
        self._log.info('PID loop for {} motor disabled.'.format(self._orientation))

    # ..........................................................................
    def close(self):
        self.close_filewriter()
        self._log.info('closed.')

    # filewriter support .......................................................

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
    def close_filewriter(self):
        if not self._filewriter_closed:
            self._filewriter_closed = True
            if self._filewriter:
                _tuning = self.get_tuning_info()
                self._filewriter.write_gnuplot_settings(_tuning)
                self._filewriter.disable()


    # formulae .................................................................

    # ..........................................................................
    @staticmethod
    def equals_zero(value):
        '''
            Returns True if the value is within 2% of 0.0.
        '''
        return numpy.isclose(value, 0.0, rtol=0.02, atol=0.0)

    # ..............................................................................
    def get_distance_cm_for_steps(self, steps):
        '''
            Provided a number of steps returns the distance traversed.
        '''
        return steps / self._steps_per_cm

    # ..............................................................................
    def get_steps_for_distance_cm(self, distance_cm):
        '''
             A function that returns the number of forward steps require to
             traverse the distance (measured in cm). Returns an int.
        '''
        '''
            Geometry Notes ...................................
    
            494 encoder steps per rotation (maybe 493)
            68.5mm diameter tires
            215.19mm/21.2cm wheel circumference
            1 wheel rotation = 215.2mm
            2295 steps per meter
            2295 steps per second  = 1 m/sec
            2295 steps per second  = 100 cm/sec
            229.5 steps per second = 10 cm/sec
            22.95 steps per second = 1 cm/sec
    
            1 rotation = 215mm = 494 steps
            1 meter = 4.587 rotations
            2295.6 steps per meter
            22.95 steps per cm
        '''
        return round(distance_cm * self._steps_per_cm)

    # ..............................................................................
    def get_forward_steps(self, rotations):
        '''
            A function that return the number of steps corresponding to the number
            of wheel rotations.
        '''
        return self._step_per_rotation * rotations

#EOF
