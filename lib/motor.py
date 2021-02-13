#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# Copyright 2020 by Murray Altheim. All rights reserved. This file is part of
# the Robot OS project and is released under the "Apache Licence, Version 2.0".
# Please see the LICENSE file included as part of this package.
#
# author:   Murray Altheim
# created:  2020-01-18
# modified: 2020-08-30
#

import sys, itertools, time
from colorama import init, Fore, Style
init()

try:
    import numpy
except ImportError:
    print(Fore.RED + "This script requires the numpy module\nInstall with: sudo pip install numpy" + Style.RESET_ALL)
    sys.exit(1)

from lib.logger import Level, Logger
from lib.enums import Orientation
from lib.slew import SlewRate
from lib.decoder import Decoder
from lib.velocity import Velocity

# ..............................................................................
class Motor():
    '''
    Establishes power control over a motor using a Hall Effect encoder
    to determine the robot's velocity and distance traveled.

    This uses the ros:motors: section of the configuration.

    :param config:      application configuration
    :param clock:       used to provide the velocity calculator with a steady
                        clock; if None velocity will always return zero
    :param tb:          reference to the ThunderBorg motor controller
    :param pi:          reference to the Raspberry Pi
    :param orientation: motor orientation
    :param level:       log level
    '''
    def __init__(self, config, clock, tb, pi, orientation, level=Level.INFO):
        global TB
        super(Motor, self).__init__()
        if config is None:
            raise ValueError('null configuration argument.')
        if clock is None:
            raise ValueError('null clock argument.')
        if tb is None:
            raise ValueError('null thunderborg argument.')
        self._tb = tb
        TB = tb
        if pi is None:
            raise ValueError('null pi argument.')
        self._pi = pi

        # configuration ....................................
        # get motors configuration section
        cfg = config['ros'].get('motors')
        # in case you wire something up backwards (we need this prior to the logger)
        self._reverse_motor_orientation = cfg.get('reverse_motor_orientation')
        # establish orientation
        if self._reverse_motor_orientation:
            self._orientation = Orientation.STBD if orientation is Orientation.PORT else Orientation.PORT
        else:
            self._orientation = orientation
        # velocity calculation .............................
#       if clock:
        self._velocity = Velocity(config, clock, self, Level.WARN)
#       else:
#           self._velocity = None
        # NOW we can create the logger
        self._log = Logger('motor:{}'.format(orientation.label), level)
        self._log.info('initialising {} motor...'.format(orientation))
        # acceleration loop delay
        self._accel_loop_delay_sec = cfg.get('accel_loop_delay_sec') # default: 0.10
        self._log.debug('acceleration loop delay: {:>5.2f} sec'.format(self._accel_loop_delay_sec))

        # TODO move this configuration to its own Decoder section
        self._log.debug('reverse motor orientation: {}'.format(self._reverse_motor_orientation))
        self._reverse_encoder_orientation = cfg.get('reverse_encoder_orientation')
        self._log.debug('reverse encoder orientation: {}'.format(self._reverse_encoder_orientation))
        # GPIO pins configured for A1, B1, A2 and B2
        self._motor_encoder_a1_port = cfg.get('motor_encoder_a1_port') # default: 22
        self._log.debug('motor encoder a1 port: {:d}'.format(self._motor_encoder_a1_port))
        self._motor_encoder_b1_port = cfg.get('motor_encoder_b1_port') # default: 17
        self._log.debug('motor encoder b1 port: {:d}'.format(self._motor_encoder_b1_port))
        self._motor_encoder_a2_stbd = cfg.get('motor_encoder_a2_stbd') # default: 27
        self._log.debug('motor encoder a2 stbd: {:d}'.format(self._motor_encoder_a2_stbd))
        self._motor_encoder_b2_stbd = cfg.get('motor_encoder_b2_stbd') # default: 18
        self._log.debug('motor encoder b2 stbd: {:d}'.format(self._motor_encoder_b2_stbd))
        # end configuration ................................

#       self._motor_power_limit = 0.80     
        self._motor_power_limit = cfg.get('motor_power_limit')  # power limit to motor
        self._log.debug('motor power limit: {:5.2f}'.format(self._motor_power_limit))
        self._over_power_counter = itertools.count()
        self._over_power_count = 0           # limit to disable motor
        self._over_power_count_limit = 4     # how many times we can be overpowered before disabling
        self._steps = 0                      # step counter
        self._max_power = 0.0                # capture maximum power applied
        self._max_driving_power = 0.0        # capture maximum adjusted power applied
        self._interrupt = False              # used to interrupt loops
        self._stepcount_timestamp = time.time()  # timestamp at beginning of velocity measurement
        self._enabled = False                # was by default enabled
        self._killed  = False                # if killed we never re-enable
        self._start_timestamp = time.time()  # timestamp at beginning of velocity measurement

        # configure encoder ................................
        self._log.info('configuring rotary encoders...')
        if self._reverse_encoder_orientation:
            if orientation is Orientation.PORT:
                self.configure_encoder(Orientation.STBD)
            else:
                self.configure_encoder(Orientation.PORT)
        else:
            self.configure_encoder(self._orientation)

        self._log.info('ready.')

    # ..............................................................................
    def configure_encoder(self, orientation):
        if self._orientation is Orientation.PORT:
            _encoder_a = self._motor_encoder_a1_port
            _encoder_b = self._motor_encoder_b1_port
        elif self._orientation is Orientation.STBD:
            _encoder_a = self._motor_encoder_a2_stbd
            _encoder_b = self._motor_encoder_b2_stbd
        else:
            raise ValueError("unrecognised value for orientation.")
        self._decoder = Decoder(self._pi, self._orientation, _encoder_a, _encoder_b, self._callback_step_count, self._log.level)
        self._log.info('configured {} motor encoder on pin {} and {}.'.format(orientation.name, _encoder_a, _encoder_b))

    # ..........................................................................
    @property
    def orientation(self):
        '''
        Returns the orientation of this motor.
        '''
        return self._orientation

    # ..........................................................................
    @property
    def velocity(self):
        if self._velocity:
            return self._velocity()
        else:
            return 0.0

    # ..........................................................................
    @property
    def enabled(self):
        return self._enabled

    # ..............................................................................
    @property
    def steps(self):
        return self._steps

    # ..............................................................................
    def reset_steps(self):
        self._over_power_count = 0
        self._steps = 0

    # ..............................................................................
    def set_max_power_ratio(self, max_power_ratio):
        self._max_power_ratio = max_power_ratio

    # ..............................................................................
    def get_max_power_ratio(self):
        return self._max_power_ratio

    # ..............................................................................
    def _callback_step_count(self, pulse):
        '''
        This callback is used to capture encoder steps.
        '''
#       self._log.info(Fore.BLACK + Style.BRIGHT + '_callback_step_count({})'.format(pulse))
        if not self._reverse_encoder_orientation:
            if self._orientation is Orientation.PORT:
                self._steps = self._steps + pulse
            else:
                self._steps = self._steps - pulse
        else:
            if self._orientation is Orientation.PORT:
                self._steps = self._steps - pulse
            else:
                self._steps = self._steps + pulse
#       self._log.info(Fore.BLACK + '{}: {:+d} steps'.format(self._orientation.label, self._steps))

    # ..........................................................................
    def enable(self):
        if not self._killed:
            if self._enabled:
                self._log.warning('already enabled.')
            else:
                self._enabled = True
                if self._velocity:
                    self._velocity.enable()
                self._log.info('enabled.')
        else:
            self._log.warning('cannot enable: motor has been killed.')

    # ..........................................................................
    def disable(self):
        if not self._enabled:
            self._log.warning('already disabled.')
        else:
            self._enabled = False
            if self._velocity:
                self._velocity.disable()
#           self.set_motor_power(0.0)
            if self._orientation is Orientation.PORT:
                self._tb.SetMotor1(0.0)
            else:
                self._tb.SetMotor2(0.0)
            self._log.info('disabled.')

    # ..........................................................................
    def close(self):
        if self.enabled:
            self.disable()
        if self._max_power > 0 or self._max_driving_power > 0:
            self._log.info('on closing: max power: {:>5.2f}; max adjusted power: {:>5.2f}.'.format(self._max_power, self._max_driving_power))
        self._log.info('closed.')

    # ..........................................................................
    def interrupt(self):
        '''
        Interrupt any loops by setting the _interrupt flag.
        '''
        self._interrupt = True

    # ..........................................................................
    def reset_interrupt(self):
        '''
        Reset the value of the _interrupt flag to False.
        '''
        self._interrupt = False

    # ..........................................................................
    @property
    def interrupted(self):
        '''
        Return the value of the _interrupt flag.
        '''
        return self._interrupt

    # ..........................................................................
    @staticmethod
    def cancel():
        '''
        Stop both motors immediately. This can be called from either motor.
        '''
        try: TB
        except NameError: TB = None

        if TB:
            TB.SetMotor1(0.0)
            TB.SetMotor2(0.0)
        else:
            print('motor             :' + Fore.YELLOW + ' WARN  : cannot cancel motors: no thunderborg available.' + Style.RESET_ALL)

    # ..........................................................................
    def is_in_motion(self):
        '''
        Returns True if the motor is moving.
        '''
        return self.get_current_power_level() > 0.0

    # ..........................................................................
    def _over_power(self):
        self._over_power_count = next(self._over_power_counter)
        self._log.warning('over powered {} times.'.format(self._over_power_count))
        if self._over_power_count >= self._over_power_count_limit:
            self._log.error('over power limit reached, disabling...')
            self.disable()
            self._killed = True # don't permit re-enabling

    # ..........................................................................
    def set_motor_power(self, power_level):
        '''
        Sets the power level to a number between 0.0 and 1.0, with the actual
        limits set by the _max_power_ratio, which alters the value to match
        the power/motor voltage ratio.
        '''
        if self._killed: # though we'll let the power be set to zero
            self._log.warning('motor killed, ignoring setting of {:<5.2f}'.format(power_level))
            return
        elif not self.enabled and power_level > 0.0: # though we'll let the power be set to zero
            self._log.warning('motor disabled, ignoring setting of {:<5.2f}'.format(power_level))
            return
        # safety checks ..........................
        if power_level > self._motor_power_limit:
            self._over_power()
            self._log.error('motor power too high: {:>5.2f}; limit: {:>5.2f}'.format(power_level, self._motor_power_limit))
            power_level = self._motor_power_limit
#           return
        elif power_level < ( -1.0 * self._motor_power_limit ):
            self._over_power()
            self._log.error('motor power too low: {:>5.2f}; limit: {:>5.2f}'.format( power_level,( -1.0 * self._motor_power_limit )))
            power_level = -1.0 * self._motor_power_limit
#           return
        _current_power = self.get_current_power_level()
#       _current_actual_power = _current_power * ( 1.0 / self._max_power_ratio )
        if abs(_current_power - power_level) > 0.3 and _current_power > 0.0 and power_level < 0:
            self._log.error('cannot perform positive-negative power jump: {:>5.2f} to {:>5.2f}.'.format(_current_power, power_level))
            return
        elif abs(_current_power - power_level) > 0.3 and _current_power < 0.0 and power_level > 0:
            self._log.error('cannot perform negative-positive power jump: {:>5.2f} to {:>5.2f}.'.format(_current_power, power_level))
            return

        # okay, let's go .........................
        _driving_power = float(power_level * self._max_power_ratio)
        self._max_power = max(power_level, self._max_power)
        self._max_driving_power = max(abs(_driving_power), self._max_driving_power)
        self._log.debug(Fore.MAGENTA + Style.BRIGHT + 'power argument: {:>5.2f}'.format(power_level) + Style.NORMAL \
                + '\tcurrent power: {:>5.2f}; driving power: {:>5.2f}.'.format(_current_power, _driving_power))
        if self._orientation is Orientation.PORT:
            self._tb.SetMotor1(_driving_power)
        else:
            self._tb.SetMotor2(_driving_power)

    # ..........................................................................
    def is_stopped(self):
        '''
         Returns true if the motor is entirely stopped.
        '''
        return ( self.get_current_power_level() == 0.0 )

    # ................................
    def get_current_power_level(self):
        '''
         Makes a best attempt at getting the power level value from the motors.
        '''
        value = None
        count = 0
        if self._orientation is Orientation.PORT:
            while value == None and count < 20:
                count += 1
                value = self._tb.GetMotor1()
                time.sleep(0.005)
        else:
            while value == None and count < 20:
                count += 1
                value = self._tb.GetMotor2()
                time.sleep(0.005)
        if value == None:
            return 0.0
        else:
            return value

    # ..........................................................................
    @staticmethod
    def velocity_to_power(velocity):
        '''
        A quick and dirty approximate conversion between a velocity in
        cm/sec and motor power, created entirely via observation of an
        OSEPP 9v motor on the KD01 robot:
    
            power   velo        power  velo
            0.0     0.0         0.50   30.0
            0.20    10.0        0.55   33.0
            0.25    12.0        0.60   36.0
            0.30    16.0        0.65   39.0
            0.35    18.0        0.70   43.0
            0.40    22.0        0.75   46.0
            0.45    25.0        0.80   50.0
    
        This provides a conversion factor of about 0.016 at the high
        end where it matters most.
        '''
        if velocity < 10.0:
            return 0.00
        elif velocity > 50.0:
            return 0.80
        else:
            return velocity * 0.016

    # motor control functions ..................................................

    # ..........................................................................
    def stop(self):
        '''
        Stops the motor immediately.
        '''
        self._log.info('stop.')
        if self._orientation is Orientation.PORT:
            self._tb.SetMotor1(0.0)
        else:
            self._tb.SetMotor2(0.0)
        pass

#    # ..........................................................................
#    def halt(self):
#        '''
#        Quickly (but not immediately) stops.
#        '''
#        self._log.info('halting...')
#        # set slew slow, then decelerate to zero
#        self.accelerate(0.0, SlewRate.FAST, -1)
#        self._log.debug('halted.')
#
    # ..........................................................................
    def brake(self):
        '''
        Slowly coasts to a stop.
        '''
        self._log.info('braking...')
        # set slew slow, then decelerate to zero
        self.accelerate(0.0, SlewRate.SLOWER, -1)
        self._log.debug('braked.')

#    # ..........................................................................
#    def ahead(self, speed):
#        '''
#        Slews the motor to move ahead at speed.
#        This is an alias to accelerate(speed).
#        '''
#        self._log.info('ahead to speed of {}...'.format(speed))
#        self.accelerate(speed, SlewRate.NORMAL, -1)
#        self._log.debug('ahead complete.')
#
#    # ..........................................................................
#    def stepAhead(self, speed, steps):
#        '''
#            Moves forwards specified number of steps, then stops.
#        '''
##       self._log.info('step ahead {} steps to speed of {}...'.format(steps,speed))
#        self.accelerate(speed, SlewRate.NORMAL, steps)
##       self._log.debug('step ahead complete.')
#        pass
#
#    # ..........................................................................
#    def astern(self, speed):
#        '''
#            Slews the motor to move astern at speed.
#            This is an alias to accelerate(-1 * speed).
#        '''
#        self._log.info('astern at speed of {}...'.format(speed))
#        self.accelerate(-1.0 * speed, SlewRate.NORMAL, -1)
#        self._log.debug('astern complete.')
#
#    # ..........................................................................
#    def stepAstern(self, speed, steps):
#        '''
#            Moves backwards specified number of steps, then stops.
#        '''
#        self._log.info('step astern {} steps to speed of {}...'.format(steps,speed))
#        self.accelerate(speed, SlewRate.NORMAL, steps)
#        self._log.debug('step astern complete.')
#        pass

    # ..........................................................................
    def accelerate(self, speed, slew_rate, steps):
        '''
        Slews the motor to the designated speed. -100 <= 0 <= speed <= 100.

        This takes into account the maximum power to be supplied to the
        motor based on the battery and motor voltages.

        If steps > 0 then run until the number of steps has been reached.
        '''
        self._interrupt = False
        _current_power_level = self.get_current_power_level()
        if _current_power_level is None:
            raise RuntimeError('cannot continue: unable to read current power from motor.')
        self._log.info('ACCELERATE:' + Fore.YELLOW + ' current power: {:>5.2f} max power ratio: {:>5.2f}...'.format(_current_power_level, self._max_power_ratio))
        _current_power_level = _current_power_level * ( 1.0 / self._max_power_ratio )

        # accelerate to desired speed
        _desired_div_100 = float(speed / 100)
        self._log.info('accelerating from {:>5.2f} to {:>5.2f}...'.format(_current_power_level, _desired_div_100))

        if _current_power_level == _desired_div_100: # no change
            self._log.warning('already at acceleration power of {:>5.2f}, exiting.'.format(_current_power_level) )
            return
        elif _current_power_level < _desired_div_100: # moving ahead
            _slew_rate_ratio = slew_rate.ratio
            overstep = 0.001
        else: # moving astern
            _slew_rate_ratio = -1.0 * slew_rate.ratio
            overstep = -0.001

        driving_power_level = 0.0
        for step_power in numpy.arange(_current_power_level, (_desired_div_100 + overstep), _slew_rate_ratio):
            driving_power_level = float( step_power * self._max_power_ratio )
            self.set_motor_power(driving_power_level)
            if self._interrupt:
                break
            time.sleep(self._accel_loop_delay_sec)

        # be sure we're powered off
        if speed == 0.0 and abs(driving_power_level) > 0.00001:
            self._log.warning('non-zero power level: {:7.5f}v; stopping completely...'.format(driving_power_level))
            if self._orientation is Orientation.PORT:
                self._tb.SetMotor1(0.0)
            else:
                self._tb.SetMotor2(0.0)

        self._log.debug('accelerate complete.')

#EOF
