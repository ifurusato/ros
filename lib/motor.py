#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# Copyright 2020 by Murray Altheim. All rights reserved. This file is part of
# the Robot OS project and is released under the "Apache Licence, Version 2.0".
# Please see the LICENSE file included as part of this package.
#
# author:   Murray Altheim
# created:  2020-01-18
# modified: 2020-04-15
#

import time
from colorama import init, Fore, Style
init()

try:
    import numpy
except ImportError:
    exit("This script requires the numpy module\nInstall with: sudo pip install numpy")

from lib.logger import Level, Logger
from lib.devnull import DevNull
from lib.enums import SlewRate, Direction, Orientation, Speed
from lib.rotary_encoder import Decoder
from lib.pid import PID


# ..............................................................................
class Motor():
    '''
        Example of a motor sequence script that uses the motor
        encoders to determine the distance traveled.

        This uses the ros:motors: section of the configuration.
    '''
    def __init__(self, config, tb, pi, orientation, level):
        global TB
        super(Motor, self).__init__()
        if config is None:
            raise ValueError('null configuration argument.')
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
        # NOW we can create the logger
        self._log = Logger('motor:{}'.format(orientation.label), level)
        self._log.info('initialising {} motor...'.format(orientation))
        self._log.debug('_reverse_motor_orientation: {}'.format(self._reverse_motor_orientation))
        self._reverse_encoder_orientation =  cfg.get('reverse_encoder_orientation')
        self._log.debug('_reverse_encoder_orientation: {}'.format(self._reverse_encoder_orientation))
        # GPIO pins configured for A1, B1, A2 and B2
        self._rotary_encoder_a1_port = cfg.get('rotary_encoder_a1_port') # default: 22
        self._log.debug('rotary_encoder_a1_port: {:d}'.format(self._rotary_encoder_a1_port))
        self._rotary_encoder_b1_port = cfg.get('rotary_encoder_b1_port') # default: 17
        self._log.debug('rotary_encoder_b1_port: {:d}'.format(self._rotary_encoder_b1_port))
        self._rotary_encoder_a2_stbd = cfg.get('rotary_encoder_a2_stbd') # default: 27
        self._log.debug('rotary_encoder_a2_stbd: {:d}'.format(self._rotary_encoder_a2_stbd))
        self._rotary_encoder_b2_stbd = cfg.get('rotary_encoder_b2_stbd') # default: 18
        self._log.debug('rotary_encoder_b2_stbd: {:d}'.format(self._rotary_encoder_b2_stbd))
        # how many pulses per encoder measurement?
        self._sample_rate = cfg.get('sample_rate') # default: 10
        self._log.debug('sample_rate: {:d}'.format(self._sample_rate))
        # convert raw velocity to approximate a percentage
        self._velocity_fudge_factor = cfg.get('velocity_fudge_factor') # default: 14.0
        self._log.debug('velocity fudge factor: {:>5.2f}'.format(self._velocity_fudge_factor))
        # limit set on power sent to motors
        self._max_power_limit = cfg.get('max_power_limit') # default: 1.2
        self._log.debug('maximum power limit: {:>5.2f}'.format(self._max_power_limit))
        # acceleration loop delay
        self._accel_loop_delay_sec = cfg.get('accel_loop_delay_sec') # default: 0.10
        self._log.debug('acceleration loop delay: {:>5.2f} sec'.format(self._accel_loop_delay_sec))
        # end configuration ................................

        self._motor_power_limit = 0.9        # power limit to motor
        self._steps = 0                      # step counter
        self._steps_begin = 0                # step count at beginning of velocity measurement
        self._velocity = 0.0                 # current velocity
        self._max_velocity = 0.0             # capture maximum velocity attained
        self._max_power = 0.0                # capture maximum power applied
        self._max_driving_power = 0.0        # capture maximum adjusted power applied
        self._interrupt = False              # used to interrupt loops
        self._stepcount_timestamp = time.time()  # timestamp at beginning of velocity measurement
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

        # create and configure PID controller ..............
        self._pid = PID(config, self, level)

        self._log.info('ready.')


    # ..............................................................................
    def get_pid_controller(self):
        '''
            Return the PID controller used for this Motor.
        '''
        return self._pid


    # ..............................................................................
    def get_velocity(self):
        return self._velocity


    # ..............................................................................
    def get_steps(self):
        return self._steps


    # ..............................................................................
    def set_max_power_ratio(self, max_power_ratio):
        self._max_power_ratio = max_power_ratio


    # ..............................................................................
    def get_max_power_ratio(self):
        return self._max_power_ratio


    # ..............................................................................
    def configure_encoder(self, orientation):
        if self._orientation is Orientation.PORT:
            ROTARY_ENCODER_A = self._rotary_encoder_a1_port
            ROTARY_ENCODER_B = self._rotary_encoder_b1_port
        elif self._orientation is Orientation.STBD:
            ROTARY_ENCODER_A = self._rotary_encoder_a2_stbd
            ROTARY_ENCODER_B = self._rotary_encoder_b2_stbd
        else:
            raise ValueError("unrecognised value for orientation.")
        self._decoder = Decoder(self._pi, ROTARY_ENCODER_A, ROTARY_ENCODER_B, self.callback_step_count)
        self._log.info('configured {} rotary encoder on pin {} and {}.'.format(orientation.name, ROTARY_ENCODER_A, ROTARY_ENCODER_B))


    # ..............................................................................
    def callback_step_count(self, pulse):
        '''
            This callback is used to capture encoder steps.
        '''
        if self._orientation is Orientation.PORT:
            self._steps = self._steps - pulse
        else:
            self._steps = self._steps + pulse
#       print('{}: {:+d} steps'.format(self._orientation.name, self._steps))
        self._log.debug(Fore.BLACK + '{}: {:+d} steps'.format(self._orientation.label, self._steps))
#       print('decoder:{}      :'.format(self._orientation.label) + Fore.BLACK + Style.DIM + ' DEBUG : {}: {:+d} steps'.format(self._orientation.label, self._steps) + Style.RESET_ALL)
        if self._steps % self._sample_rate == 0:
            if self._steps_begin != 0:
                self._velocity = ( (self._steps - self._steps_begin) / (time.time() - self._stepcount_timestamp) / self._velocity_fudge_factor ) # steps / duration
                self._max_velocity = max(self._velocity, self._max_velocity)
#               self._log.debug("{:d} steps;\tvelocity: {:>5.1f}/{:>5.1f}".format(self._steps, self._velocity, self._max_velocity))
                self._stepcount_timestamp = time.time()
            self._stepcount_timestamp = time.time()
            self._steps_begin = self._steps


    # ..............................................................................
    def cruise():
        '''
            Cruise at the current speed.
        '''
        pass # TODO


    # ..........................................................................
    def enable(self):
        self._log.info('enabled.')
        pass


    # ..........................................................................
    def disable(self):
        self._log.info('disabled.')
        pass


    # ..........................................................................
    def close(self):
        if self._pid:
            self._pid.close()
        self._log.info('max velocity: {:>5.2f}; max power: {:>5.2f}; max adjusted power: {:>5.2f}.'.format(self._max_velocity, self._max_power, self._max_driving_power))
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
    def is_interrupted(self):
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


#   Motor Functions ............................................................

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


    # ..........................................................................
    def halt(self):
        '''
            Quickly (but not immediately) stops.
        '''
        self._log.info('halting...')
        # set slew slow, then decelerate to zero
        self.accelerate(0.0, SlewRate.FAST, -1)
        self._log.debug('halted.')


    # ..........................................................................
    def brake(self):
        '''
            Slowly coasts to a stop.
        '''
        self._log.info('braking...')
        # set slew slow, then decelerate to zero
        self.accelerate(0.0, SlewRate.SLOWER, -1)
        self._log.debug('braked.')


    # ..........................................................................
    def ahead(self, speed):
        '''
            Slews the motor to move ahead at speed.
            This is an alias to accelerate(speed).
        '''
        self._log.info('ahead to speed of {}...'.format(speed))
#       self._decoder.set_clockwise(True) # TEMP
        self.accelerate(speed, SlewRate.NORMAL, -1)
        self._log.debug('ahead complete.')


    # ..........................................................................
    def stepAhead(self, speed, steps):
        '''
            Moves forwards specified number of steps, then stops.
        '''
#       self._log.info('step ahead {} steps to speed of {}...'.format(steps,speed))
#       self._decoder.set_clockwise(True) # TEMP
        self.accelerate(speed, SlewRate.NORMAL, steps)
#       self._log.debug('step ahead complete.')
        pass


    # ..........................................................................
    def astern(self, speed):
        '''
            Slews the motor to move astern at speed.
            This is an alias to accelerate(-1 * speed).
        '''
        self._log.info('astern at speed of {}...'.format(speed))
#       self._decoder.set_clockwise(False) # TEMP
        self.accelerate(-1.0 * speed, SlewRate.NORMAL, -1)
#       self._decoder.set_clockwise(True) # TEMP
        self._log.debug('astern complete.')


    # ..........................................................................
    def stepAstern(self, speed, steps):
        '''
            Moves backwards specified number of steps, then stops.
        '''
        self._log.info('step astern {} steps to speed of {}...'.format(steps,speed))
#       self._decoder.set_clockwise(False) # TEMP
        self.accelerate(speed, SlewRate.NORMAL, steps)
        self._log.debug('step astern complete.')
        pass


    # ..........................................................................
    def is_in_motion(self):
        '''
            Returns true if the motor is moving.
        '''
        return self.get_current_power_level() > 0.0


    # ..........................................................................
    def accelerate_to_velocity(self, velocity, slew_rate, steps):
        '''
            Slews the motor to the requested velocity.

            If steps is greater than zero it provides a step limit.
        '''
        if steps > 0:
            _step_limit = self._steps + steps
            self._log.critical('>>>>>>  {} steps, limit: {}.'.format(self._steps, _step_limit))
        else:
            _step_limit = -1

        if self._velocity == velocity: # if current velocity equals requested, no need to accelerate
            self._log.info('NO CHANGE: ALREADY AT velocity {:>5.2f}/{:>5.2f}.'.format(self._velocity, velocity))
            return

        # accelerate to target velocity...
        self._accelerate_to_velocity(velocity, slew_rate, _step_limit)

        # now maintain velocity...
        self.maintain_velocity(velocity, _step_limit)

        self._log.info(Fore.BLUE + Style.BRIGHT + 'accelerated to velocity {:>5.2f} at power: {:>5.2f}. '.format(velocity, self.get_current_power_level()))


    # ..........................................................................
    def _accelerate_to_velocity(self, velocity, slew_rate, step_limit):
        _current_power_level = self.get_current_power_level() * ( 1.0 / self._max_power_ratio )
        self._log.info(Fore.BLUE + Style.BRIGHT + '_accelerate_to_velocity {:>5.2f} @ slew rate: {:>5.2f}; current power: {:>5.2f}; step limit: {:+d}'.format(velocity, slew_rate.ratio, _current_power_level, step_limit))
        if self._velocity < velocity: # if current velocity is less than requested, speed up
            # note that steps count down when going in reverse
            self._log.info('NEED TO SPEED UP TO velocity {:>5.2f}/{:>5.2f}.'.format(self._velocity, velocity))
            while self._velocity < velocity and ( step_limit == -1 or self._steps <= step_limit ):
                _current_power_level += slew_rate.ratio
                # FIXME as we get closer to our goal we tend to bounce
                driving_power_level = float(_current_power_level * self._max_power_ratio)
                self.set_motor_power(driving_power_level)
                if self._orientation is Orientation.PORT:
                    self._log.info( Fore.RED   + 'INCREASE: ' + Fore.CYAN + 'velocity {:>5.2f} < {:>5.2f};\t{:+d} of {:+d} steps;\tcurrent power: {:>5.2f}.'.format(\
                            self._velocity, velocity, self._steps, step_limit, _current_power_level))
                else:
                    self._log.info( Fore.GREEN + 'INCREASE: ' + Fore.CYAN + 'velocity {:>5.2f} < {:>5.2f};\t{:+d} of {:+d} steps;\tcurrent power: {:>5.2f}.'.format(\
                            self._velocity, velocity, self._steps, step_limit, _current_power_level))
                if self._interrupt:
                    break
                time.sleep(0.1)

        elif self._velocity > velocity: # if current velocity is greater than requested, slow down
            self._log.info('NEED TO SLOW DOWN TO velocity {:>5.2f}/{:>5.2f}.'.format(self._velocity, velocity))
            while self._velocity > velocity and ( step_limit == -1 or self._steps <= step_limit  ):
                _current_power_level -= slew_rate.ratio
                # FIXME as we get closer to our goal we tend to bounce
                driving_power_level = float(_current_power_level * self._max_power_ratio)
                self.set_motor_power(driving_power_level)
                if self._orientation is Orientation.PORT:
                    self._log.info( Fore.RED   + 'DECREASE: ' + Fore.BLUE + 'WHILE velocity {:>5.2f} < {:>5.2f}: steps: {} of {}; current power level: {:>5.2f}.'.format(\
                            self._velocity, velocity, self._steps, step_limit, _current_power_level))
                else:
                    self._log.info( Fore.GREEN + 'DECREASE: ' + Fore.BLUE + 'WHILE velocity {:>5.2f} < {:>5.2f}: steps: {} of {}; current power level: {:>5.2f}.'.format(\
                            self._velocity, velocity, self._steps, step_limit, _current_power_level))
                if self._interrupt:
                    break
                time.sleep(0.1)
#               self._log.info(Fore.CYAN + 'WHILE velocity {:>5.2f} < {:>5.2f}: current power level: {:>5.2f}.'.format(self._velocity,velocity, _current_power_level))


    # ..........................................................................
    def maintain_velocity(self, velocity, step_limit):
        '''
            Maintain the specified velocity, using the current power level at the beginning of the call.
        '''
        _current_power_level = self.get_current_power_level() * ( 1.0 / self._max_power_ratio )
        self._log.info('maintain velocity {:>5.2f} @ power level: {:>5.2f}.'.format(velocity, _current_power_level))
        _slew_rate_ratio = SlewRate.EXTREMELY_SLOW.ratio # 0.0034
        while self._steps < step_limit or step_limit == -1:
            _diff = self._velocity - velocity
            if _diff < 0.0: # if current velocity is less than requested, speed up
                _current_power_level = min(_current_power_level + _slew_rate_ratio, self._max_power_limit)
                driving_power_level = float(_current_power_level * self._max_power_ratio)
                self._log.info(Fore.GREEN + 'INCREASE:' + Fore.CYAN + ' velocity {:>5.2f} ({:+.02f});'.format(self._velocity, _diff) \
                        + Fore.BLACK + ' current power: {:>5.2f};\tdriving power: {:>5.2f}.'.format(driving_power_level, _current_power_level) + Style.DIM + ';\t{:+d} steps.'.format(self._steps))
                self.set_motor_power(driving_power_level)
                if self._interrupt:
                    break
            elif _diff > 0.0: # if current velocity is greater than requested, slow down
                _current_power_level = max(_current_power_level - _slew_rate_ratio, -1.0 * self._max_power_limit)
                driving_power_level = float(_current_power_level * self._max_power_ratio)
                self._log.info(Fore.RED + 'DECREASE:' + Fore.CYAN + ' velocity {:>5.2f} ({:+.02f});'.format(self._velocity, _diff) \
                        + Fore.BLACK + ' current power: {:>5.2f};\tdriving power: {:>5.2f}.'.format(driving_power_level, _current_power_level) + Style.DIM + ';\t{:+d} steps.'.format(self._steps))
                self.set_motor_power(driving_power_level)
                if self._interrupt:
                    break
            time.sleep(0.05)
        self._interrupt = False


    # ..........................................................................
    def ahead_for_steps(self, speed, steps):
        '''
            A test method that runs the motor ahead at the provided Speed,
            returning once the number of steps have been reached. As this
            provides for no slewing, in order to not put too much stress on
            the motor, do not call with a high speed.
        '''
        _BRAKING = False
        _current_steps = self._steps # current steps
        _braking_range = 500 if steps > 1000 else 100
        _speed = speed / 100.0
        _power = float(_speed * self._max_power_ratio)
        if _BRAKING:
            self._log.info(Fore.YELLOW + 'ahead at speed {:>5.2f} using power {:>5.2f} for steps: {:d} with braking range of {:d}.'.format(_speed, _power, steps, _braking_range))
        else:
            self._log.info(Fore.YELLOW + 'ahead at speed {:>5.2f} using power {:>5.2f} for steps: {:d} with no braking range.'.format(_speed, _power, steps))
        self.set_motor_power(_power)

        if speed >= 0:

            if _BRAKING:
                _step_limit = _current_steps + steps - _braking_range
                while self._steps < _step_limit:
                    self._log.info('{:d}/{:d} steps.'.format(self._steps, _step_limit))
                    if self._interrupt:
                        break
                    time.sleep(0.01)
                # now brake to stop ........................
                _braking_step_limit = _current_steps + steps
                while self._steps < _braking_step_limit:
                    _speed = max(0.20 , _speed - 0.001)
                    _power = float(_speed * self._max_power_ratio)
                    self.set_motor_power(_power)
                    self._log.info(Fore.RED + '{:d}/{:d} steps at speed/power: {:>5.2f}/{:>5.2f}.'.format(self._steps, _braking_step_limit, _speed, _power))
                    if self._interrupt:
                        break
                    time.sleep(0.01)
            else:
                _step_limit = _current_steps + steps
                while self._steps < _step_limit:
                    _near_end = self._steps > _step_limit - 494
                    if _near_end:
                        self._log.debug(Fore.CYAN + Style.BRIGHT + '{:d}/{:d} steps.'.format(self._steps, _step_limit))
                    else:
                        self._log.debug('{:d}/{:d} steps.'.format(self._steps, _step_limit))
                    if self._interrupt:
                        break
                    time.sleep(0.01)


        else:
            _step_limit = _current_steps - steps + _braking_range
            while self._steps > _step_limit:
                self._log.info('{:d}/{:d} steps.'.format(self._steps, _step_limit))
                if self._interrupt:
                    break
                time.sleep(0.01)
            # now brake to stop ........................
            _braking_step_limit = _current_steps - steps
            while self._steps > _braking_step_limit:
                _speed = min(0.25 , _speed + 0.002)
                _power = float(_speed * self._max_power_ratio)
                self.set_motor_power(_power)
                self._log.info(Fore.RED + '{:d}/{:d} steps at speed/power: {:>5.2f}/{:>5.2f}.'.format(self._steps, _braking_step_limit, _speed, _power))
                if self._interrupt:
                    break
                time.sleep(0.01)

        self.stop()
        self._interrupt = False


    # ..........................................................................
    def step_to(self, steps):
        '''
            Advances the motor to the requested step count, attempting to stop on that mark.
            This exits if we're not moving.
        '''
        if steps <= 0:
            self._log.warning('can\'t advance to step: argument less than zero.')
            return
        elif not self.is_in_motion():
            self._log.warning('can\'t advance to step: we\re not moving.')
            return
        elif self._velocity == 0.0: 
            self._log.warning('can\'t advance to step: we have no velocity.')
            return
        elif steps < self._steps:
            self._log.warning('can\'t advance to step: we\re already past the point.')
            return
 
        orient = Fore.RED if self._orientation is Orientation.PORT else Fore.GREEN

        # maintain velocity until within braking range
        braking_range = steps - 500
        while self._steps <= braking_range:
            self._log.info( orient + 'step {:+d} of {:+d}.'.format(self._steps, steps))
            time.sleep(0.1)

        self._log.info( orient + 'BRAKING from step {:+d}.'.format(self._steps))
        # now crawl to the end...
        _speed = Speed.DEAD_SLOW.value
        _slew_rate = SlewRate.NORMAL
        _desired_div_100 = float(_speed / 100.0)
        _current_power_level = self.get_current_power_level()
        self._log.info( orient + 'accelerating from {:>5.2f} to {:>5.2f}...'.format(_current_power_level, _desired_div_100))
        if _current_power_level == _desired_div_100: # no change
            self._log.warning( orient + 'already at acceleration power of {:>5.2f}, exiting.'.format(_current_power_level) )
            return
        elif _current_power_level < _desired_div_100: # moving ahead
            _slew_rate_ratio = _slew_rate.ratio
            overstep = 0.001
        else: # moving astern
            _slew_rate_ratio = -1.0 * _slew_rate.ratio
            overstep = -0.001

        self._log.warning(orient + Style.BRIGHT + 'LOOP from {:>5.2f} to limit: {:>5.2f} with slew: {:>5.2f}'.format(_current_power_level, (_desired_div_100 + overstep), _slew_rate_ratio))

        driving_power_level = 0.0
        for step_power in numpy.arange(_current_power_level, (_desired_div_100 + overstep), _slew_rate_ratio):
            driving_power_level = float( step_power * self._max_power_ratio )
            self.set_motor_power(driving_power_level)
            if self._interrupt:
                break
            time.sleep(self._accel_loop_delay_sec)

        self._log.info( orient + 'FINISHED BRAKING from step {:+d}.'.format(self._steps))


#       braking_power_level = _current_power_level * 0.5
#       if self._orientation is Orientation.PORT:
#           self._tb.SetMotor1(braking_power_level)
#       else:
#           self._tb.SetMotor2(braking_power_level)
#       while self._steps <= steps:
#           self._log.info( orient + 'step {:+d} of {:+d}. BRAKING...'.format(self._steps, steps))
#           time.sleep(0.1)

        # now halt entirely
        self.halt()
        self._log.info('BREAK FROM STEP TO loop at step {:+d}.'.format(self._steps))
      

    # ..........................................................................
    def set_motor_power(self, power_level):
        '''
            Sets the power level to a number between 0.0 and 1.0, with the 
            actual limits set both by the _max_driving_power limit and by
            the _max_power_ratio, which alters the value to match the 
            power/motor voltage ratio.
        '''
        # safety checks ..........................
        if power_level > self._motor_power_limit:
            self._log.error(Style.BRIGHT + 'motor power too high: {:>5.2f}.'.format( power_level))
            return
        elif power_level < ( -1.0 * self._motor_power_limit ):
            self._log.error(Style.BRIGHT + 'motor power too low: {:>5.2f}.'.format( power_level))
            return
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
        self._log.debug(Fore.MAGENTA + Style.BRIGHT + 'power argument: {:>5.2f}'.format(power_level) + Style.NORMAL + '\tcurrent power: {:>5.2f}; driving power: {:>5.2f}.'.format(_current_power, _driving_power))
        if self._orientation is Orientation.PORT:
            self._tb.SetMotor1(_driving_power)
        else:
            self._tb.SetMotor2(_driving_power)


    # ..........................................................................
    def accelerate_to_zero(self, slew_rate):
        '''
            Slews the motor to a stop.
        '''
        _current_power_level = self.get_current_power_level() * (1.0 / self._max_power_ratio)
        if self._velocity == 0.0: # if current velocity equals zero, do nothing
            self._log.info('NO CHANGE: ALREADY STOPPED.')
            return
        elif self._velocity < 0.0: # if current velocity is in reverse
            self._log.info('NEED TO SPEED UP TO ZERO.')
            while self._velocity < 0.0:
                driving_power_level = float(_current_power_level * self._max_power_ratio)
                set_motor_power(driving_power_level)
                if self._interrupt:
                    break
                _current_power_level += slew_rate.ratio
                time.sleep(0.1)
                self._log.info(Fore.CYAN + 'WHILE velocity {:>5.2f} < zero: current power level: {:>5.2f}.'.format(self._velocity, _current_power_level))

        elif self._velocity > 0.0: # if current velocity is greater than zero, slow to a stop
            self._log.info('NEED TO SLOW DOWN TO zero')
            while self._velocity > 0.0:
                driving_power_level = float(_current_power_level * self._max_power_ratio)
                set_motor_power(driving_power_level)
                if self._interrupt:
                    break
                _current_power_level -= slew_rate.ratio
                time.sleep(0.1)
                self._log.info(Fore.CYAN + 'WHILE velocity {:>5.2f} > zero: current power level: {:>5.2f}.'.format(self._velocity, _current_power_level))

        time.sleep(2)
        self._log.info(Fore.BLUE + 'BREAK LOOP (accelerate to zero) at power: {:>5.2f}. '.format(self.get_current_power_level()))

        time.sleep(2)

        # be sure we're entirely powered off
        if self.get_current_power_level() > 0.0:
            if self._orientation is Orientation.PORT:
                self._tb.SetMotor1(0.0)
            else:
                self._tb.SetMotor2(0.0)

        time.sleep(2)


    # ..........................................................................
    def accelerate(self, speed, slew_rate, steps):
        '''
            Slews the motor to the designated speed. -100 <= 0 <= speed <= 100.

            This takes into account the maximum power to be supplied to the
            motor based on the battery and motor voltages.

            If steps > 0 then run tuntil the number of steps has been reached.
        '''
        self._interrupt = False
        _current_power_level = self.get_current_power_level()
        if _current_power_level is None:
            raise RuntimeError('cannot continue: unable to read current power from motor.')
        self._log.info('current power: {:>5.2f} max power ratio: {:>5.2f}...'.format(_current_power_level, self._max_power_ratio))
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

#       self._log.warning(Style.BRIGHT + 'LOOP from {:>5.2f} to limit: {:>5.2f} with slew: {:>5.2f}'.format(_current_power_level, (_desired_div_100 + overstep), _slew_rate_ratio))

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
        return


    '''
        These two methods store the last set value of each motor.
        This is actually set from z_motor.
    '''
    def set_last_set_power(self, orientation, value):
        if orientation is Orientation.PORT:
#           self._last_set_power[0] = value
#           self._log.debug('set_last_set_power({},{:6.1f})'.format(orientation, self._last_set_power[0]))
            pass
        else:
#           self._last_set_power[1] = value
#           self._log.debug('set_last_set_power({},{:6.1f})'.format(orientation, self._last_set_power[1]))
            pass


    # ..........................................................................
    def get_orientation(self):
        '''
            Returns the orientation of this motor.
        '''
        return self._orientation


    # ..........................................................................
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
    def is_stopped(self):
        '''
            Returns true if the motor is entirely stopped.
        '''
        return ( self.get_current_power_level() == 0.0 )


#EOF
