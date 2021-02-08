#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# Copyright 2020 by Murray Altheim. All rights reserved. This file is part of
# the Robot OS project and is released under the "Apache Licence, Version 2.0".
# Please see the LICENSE file included as part of this package.
#
# author:   Murray Altheim
# created:  2020-09-13
# modified: 2020-09-13
#
# Unlike other enums this one requires configuration as it involves the
# specifics of the motor encoders and physical geometry of the robot.
# Unconfigured it always returns 0.0, which is harmless but not useful.

import sys, math, time
from colorama import init, Fore, Style
init()

from lib.enums import Orientation
from lib.message import Message
from lib.event import Event
from lib.logger import Level, Logger

# ..............................................................................
class Velocity(object):
    '''
    Velocity is a property of a motor, and therefore this class is meant
    to be instantiated on a motor. It is used to calculate velocity by
    capturing the step count from a motor encoder, where a specific number
    of encoder ticks/steps per second corresponds to a given velocity,
    which can be converted to an SI unit (e.g., cm/sec).

        Based on some hardware constants from the robot:

          68.0mm diameter tires
          213.62830mm/21.362830cm wheel circumference
          494 encoder steps per rotation

        we can noodle around and deduce various related values:

          494 steps = 213.62830mm
          494 steps = 21.362830cm

          2312.4278 steps per meter
          23.124278 steps per cm
          2.3124278 steps per mm

          4.681028 rotations per meter
          0.04681028 rotations per cm
          0.004681028 rotations per mm
          0.432445952mm per step

        further deriving:

          1 wheel rotation/sec = 21.362830cm/sec
          494 steps/minute = 8.2333 steps/second @ 1rpm
          4940 steps/minute = 82.3333 steps/second @ 10rpm
          49400 steps/minute = 823.3333 steps/second @ 100rpm
          1 rps = 494 steps/second = 21.362830cm/sec

          2312.4278 steps per second @ 1 m/sec
          2312.4278 steps per second @ 100 cm/sec
          231.24278 steps per second @ 10 cm/sec
          23.124278 steps per second @ 1 cm/sec
          1 cm/sec = 23.124278 steps/sec

        And so for our 50ms (20Hz) loop:

          1/20th wheel rotation = 24.7 steps
          1/20th rotation = 1.06815cm
          1/20th rotation = 10.6815mm
          1.1562139 steps per 1/20th sec @ 1 cm/sec

        The most important for our purposes being:

          494 steps/sec = 21.362830cm/sec

        If we wish to calculate velocity in cm/sec we need to find out how many steps
        have occurred since the last function call, then use that to obtain velocity.

        But this is only true if our duty cycle is exactly 20Hz, which it's not. So
        to properly calculate how many steps we might expect in a certain number of
        milliseconds, we go back to our earlier deduction:

          2312.4278 steps per 1000ms = 1 cm/sec
          2.3124278 steps per 1ms = 1 cm/sec

        and multiply that constant times the number of milliseconds passed since the
        last function call.

    TODO:
      a. measure unloaded wheel speed at maximum power (in steps per second,
         from encoders) to obtain maximum velocity as upper limit
      b. figure out how many steps per second the upper limit represents
    '''
    def __init__(self, config, clock, motor, level=Level.INFO):
        if config is None:
            raise ValueError('null configuration argument.')
        if clock is None:
            raise ValueError('null clock argument.')
        self._clock = clock
        self._freq_hz = clock.freq_hz
        self._period_ms = 1000.0 / self._freq_hz
        if motor is None:
            raise ValueError('null motor argument.')
        self._motor = motor
#       self._log = Logger('velocity:{}'.format(motor.orientation.label), level)
        self._log = Logger('velocity:{}'.format(motor.orientation.label), Level.INFO)
        # now calculate some geometry-based conversions
        _config = config['ros'].get('geometry')
        self._steps_per_rotation  = _config.get('steps_per_rotation') # 494 encoder steps per wheel rotation
        self._log.info('{:d} encoder steps/rotation'.format(self._steps_per_rotation))
        self._wheel_diameter      = _config.get('wheel_diameter') # 68.0mm
        self._log.info('wheel diameter:     \t{:4.1f}mm'.format(self._wheel_diameter))
        self._wheel_circumference = self._wheel_diameter * math.pi / 10.0
        self._log.info('wheel circumference:\t{:7.4f}cm'.format(self._wheel_circumference))
        # convert raw velocity to approximate a percentage
        self._steps_per_cm = self._steps_per_rotation / self._wheel_circumference
        self._log.info('conversion constant:\t{:7.4f} steps/cm'.format(self._steps_per_cm))
        # sanity check: perform conversion for velocity of 1 wheel rotation (494 steps)
        # per second, where the returned value should be the circumference (21.36cm)
        _test_velocity = self.steps_to_cm(self._steps_per_rotation)
        self._log.info(Fore.GREEN + 'example conversion:\t{:7.4f}cm/rotation'.format(_test_velocity))
        assert _test_velocity == self._wheel_circumference
        # ..............................
        self._stepcount_timestamp = None
        self._steps_begin  = 0      # step count at beginning of velocity measurement
        self._velocity     = 0.0    # current velocity
        self._max_velocity = 0.0    # capture maximum velocity attained
        self._enabled      = False
        self._closed       = False
        self._log.info('ready.')

    # ..............................................................................
    def steps_to_cm(self, steps):
        return steps / self._steps_per_cm

    # ......................................................
    def handle_message(self, message):
        self._log.warning('handle_message() triggered.')
        self.add(message)

    # ..........................................................................
    def add(self, message):
        '''
        This receives a TICK message every 50ms (i.e., at 20Hz), calculating
        velocity based on the tick/step count of the motor encoder.
        '''
        self._log.warning('add() triggered.')
        if self._enabled and ( message.event is Event.CLOCK_TICK or message.event is Event.CLOCK_TOCK ):
            if self._motor.enabled: # then calculate velocity from motor encoder's step count
                _time_diff_ms = 0.0
                _steps = self._motor.steps
                if self._steps_begin != 0:
                    _time_diff_sec = time.time() - self._stepcount_timestamp
                    _time_diff_ms = _time_diff_sec * 1000.0
                    _time_error_ms = self._period_ms - _time_diff_ms
                    # we multiply our step count by the percentage error to obtain
                    # what would be the step count for our 50.0ms period
                    _diff_steps = _steps - self._steps_begin
                    _time_error_percent = _time_error_ms / self._period_ms
                    _corrected_diff_steps = _diff_steps + ( _diff_steps * _time_error_percent )
                    # multiply the steps per period by the loop frequency (20) to get steps/second
                    _steps_per_sec = _corrected_diff_steps * self._freq_hz
                    _cm_per_sec = self.steps_to_cm(_steps_per_sec)
                    self._velocity = _cm_per_sec
                    self._max_velocity = max(self._velocity, self._max_velocity)
                    self._log.info(Fore.BLUE + '{:+d} steps, {:+d}/{:5.2f} diff/corrected; time diff: {:>5.2f}ms; error: {:>5.2f}%;\t'.format(\
                            self._motor.steps, _diff_steps, _corrected_diff_steps, _time_diff_ms, _time_error_percent * 100.0) \
                            + Fore.YELLOW + 'velocity: {:>5.2f} steps/sec; {:<5.2f}cm/sec'.format(_steps_per_sec, self._velocity))
                self._stepcount_timestamp = time.time()
                self._steps_begin = _steps
            else:
                self._log.warning('add() failed: motor disabled.')
                self._velocity = 0.0
        else:
            self._velocity = 0.0 # or None?
        return self._velocity

    # ..............................................................................
    def __call__(self):
        '''
        Enables this class to be called as if it were a function, returning
        the current velocity value.
        '''
#       self._log.info(Fore.BLUE + '__call__() {:+d} steps; RETURN velocity: {:<5.2f}'.format(self._motor.steps, self._velocity))
        return self._velocity

    # ..............................................................................
    @property
    def max_velocity(self):
        return self._max_velocity

    # ..........................................................................
    def enable(self):
        if not self._closed:
            self._enabled = True
            self._clock.message_bus.add_handler(Message, self)
#           self._clock.message_bus.add_handler(Message, self.add)
            self._log.info(Fore.YELLOW + 'enabled.')
        else:
            self._log.warning('cannot enable: already closed.')

    # ..........................................................................
    def disable(self):
        if self._enabled:
            self._enabled = False
            self._log.info('disabled.')
        else:
            self._log.warning('already disabled.')

    # ..........................................................................
    def close(self):
        self.disable()
        self._closed = True
        self._log.info('closed.')

#EOF
