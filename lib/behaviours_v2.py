#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# Copyright 2020 by Murray Altheim. All rights reserved. This file is part of
# the Robot OS project and is released under the "Apache Licence, Version 2.0".
# Please see the LICENSE file included as part of this package.
#

import sys, time, random, threading
from colorama import init, Fore, Style
init()

from lib.enums import Speed, Orientation
from lib.logger import Level, Logger
from lib.ifs import IntegratedFrontSensor
from lib.rgbmatrix import RgbMatrix, Color, DisplayType
from lib.pid_v4 import PIDController
from lib.slew import SlewRate
from lib.geometry import Geometry
from lib.rate import Rate

class Behaviours():
    '''
        This class provides avoidance and some other relatively simple behaviours.

        This version uses the PID controller rathen than directly driving the motors.
    '''
    def __init__(self, config, pid_motor_controller, level):
        self._log = Logger("behave", level)
        if config is None:
            raise ValueError('null configuration argument.')
        self._geo = Geometry(config, level)
        _config = config['ros'].get('behaviours')
        self._accel_range_cm     = _config.get('accel_range_cm')
        self._cruising_velocity  = _config.get('cruising_velocity') 
        self._targeting_velocity = _config.get('targeting_velocity') 
        self._ifs = None # set later
        self._pid_motor_controller = pid_motor_controller
        _pid_controllers = pid_motor_controller.get_pid_controllers()
        self._port_pid = _pid_controllers[0]
        self._stbd_pid = _pid_controllers[1]
        self._rgbmatrix = RgbMatrix(Level.INFO)
        self._fast_speed = 99.0
        self._slow_speed = 50.0
        self._log.info('ready.')

    # ..........................................................................
    def set_ifs(self, ifs):
        self._ifs = ifs

    # ..........................................................................
    def get_cruising_velocity(self):
        return self._cruising_velocity

    # ..........................................................................
    def back_up(self, duration_sec):
        '''
            Back up for the specified duration so we don't hang our bumper.
        '''
        self._log.info('back up.')
#       self._motors.astern(self._fast_speed)
#       time.sleep(duration_sec)
        pass

    # ==========================================================================
    # one_meter .....................................................................
    '''
        The configuration defines an 'acceleration range', which is the range used
        for both acceleration and deceleration. If the travel distance is greater
        than twice this range we have enough room to reach cruising speed before
        beginning to decelerate to the step target. We also define a targeting speed,
        which is a low velocity from which we are prepared to immediately halt upon
        reaching our step target.
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

    def _one_meter(self, pid, callback):
        '''
           Threaded method for one_meter, one for each PID controller.
           This will enabled the PID if not already enabled.
        '''
        _current_steps = pid.steps # get this quickly

        _rate = Rate(20)
        if not pid.enabled:       
            pid.enable()
        pid.set_slew_rate(SlewRate.SLOWER)
        pid.enable_slew(True)

        # self._geo.steps_for_distance_cm
        _distance_cm = 200.0 # should be 1m
        _target_step_count = _distance_cm * self._geo.steps_per_cm
        _target_steps = round(_current_steps + _target_step_count)
        _closing_target_steps = _target_steps - self._geo.steps_per_rotation

        # last wheel rotation
        _final_target_step_count = _target_steps - ( 1 * self._geo.steps_per_rotation )

        _proposed_accel_range_cm = _distance_cm / 4.0
        if _proposed_accel_range_cm * 2.0 >= self._accel_range_cm: # is the proposed range greater than the standard range?
            # then we use standard acceleration/deceleration
            self._log.info('using standard accel/decel range (compressed: {:5.2f}cm; standard: {:5.2f}cm)'.format(_proposed_accel_range_cm, self._accel_range_cm))
            _accel_range_cm = self._accel_range_cm
        else: # otherwise compress to just one fourth of distance
            self._log.info('using compressed accel/decel range (compressed: {:5.2f}cm; standard: {:5.2f}cm)'.format(_proposed_accel_range_cm, self._accel_range_cm))
            _accel_range_cm = _proposed_accel_range_cm

        _accel_range_steps = round(_accel_range_cm * self._geo.steps_per_cm)
        self._log.info('using accel/decel range of {:5.2f}cm, or {:d} steps.'.format(_accel_range_cm, _accel_range_steps))

        _accel_target_steps = _current_steps + _accel_range_steps  # accelerate til this step count
        _decel_target_steps = _target_steps  - _accel_range_steps  # step count when we begin to decelerate

        self._log.info(Fore.YELLOW + 'begin one meter travel for {} motor accelerating from {:d} to {:d} steps, then cruise until {:d} steps, when we decelerate to {:d} steps and halt.'.format(\
                pid.orientation.label, _current_steps, _accel_target_steps, _decel_target_steps, _target_steps))

        _actually_do_this = True

        if _actually_do_this:
#           _accel_velocity = 0
            # accelerate to cruising velocity ............................................
#           self._rgbmatrix.show_color(Color.CYAN, Orientation.STBD)
            self._log.info(Fore.YELLOW + '{} motor accelerating...'.format(pid.orientation.label))
            while pid.steps < _accel_target_steps:
                pid.velocity = self._cruising_velocity
                _rate.wait()
         
            # cruise until 3/4 of range ..................................................
            self._log.info(Fore.YELLOW + '{} motor reached cruising velocity...'.format(pid.orientation.label))
#           self._rgbmatrix.show_color(Color.GREEN, Orientation.STBD)
            pid.velocity = self._cruising_velocity
            while pid.steps < _decel_target_steps: # .....................................
                _rate.wait()
    
            # slow down until we reach 9/10 of range
#           self._rgbmatrix.show_color(Color.YELLOW, Orientation.STBD)
            pid.velocity = round(( self._cruising_velocity + self._targeting_velocity ) / 2.0)
            while pid.steps < _decel_target_steps: # .....................................
                _rate.wait()

#           self._rgbmatrix.show_color(Color.ORANGE, Orientation.STBD)
            self._log.info(Fore.YELLOW + '{} motor reached 9/10 of target, decelerating to targeting velocity...'.format(pid.orientation.label))
            pid.set_slew_rate(SlewRate.NORMAL)
            # decelerate to targeting velocity when we get to one wheel revo of target ...
            pid.velocity = self._targeting_velocity 
            while pid.steps < _closing_target_steps: # ...................................
                _rate.wait()

#           self._rgbmatrix.show_color(Color.RED, Orientation.STBD)
            pid.velocity = self._targeting_velocity 
            while pid.steps < _target_steps: # ...........................................
#               self._log.info(Fore.YELLOW + Style.DIM + '{:d} steps...'.format(pid.steps))
                time.sleep(0.001)
            pid.velocity = 0.0
#           self._rgbmatrix.show_color(Color.BLACK, Orientation.STBD)
            self._log.info(Fore.YELLOW + '{} motor stopping...'.format(pid.orientation.label))
    
        time.sleep(1.0)
        pid.set_slew_rate(SlewRate.NORMAL)

        self._log.info(Fore.YELLOW + 'executing {} callback...'.format(pid.orientation.label))
        callback()
        self._rgbmatrix.disable()
#       pid.reset()
#       pid.disable()
        self._log.info(Fore.YELLOW + 'one meter on {} motor complete: {:d} of {:d} steps.'.format(pid.orientation.label, pid.steps, _target_steps))

    def one_meter(self):
        '''
           A behaviour that drives one meter forward in a straight line, accelerating and decelerating to hit the target exactly.
        '''
        self._log.info('start one meter travel...')
        self._one_meter_port_complete = False
        self._one_meter_stbd_complete = False
        _tp = threading.Thread(target=self._one_meter, args=(self._port_pid, self._one_meter_callback_port))
        _ts = threading.Thread(target=self._one_meter, args=(self._stbd_pid, self._one_meter_callback_stbd))
        _tp.start()
        _ts.start()
        _tp.join()
        _ts.join()
        self._log.info('one meter travel complete.')

    # ..........................................................................
    def _one_meter_callback_port(self):
        self._log.info(Fore.RED   + 'port one meter complete.')
        self._one_meter_port_complete = True

    # ..........................................................................
    def _one_meter_callback_stbd(self):
        self._log.info(Fore.GREEN + 'stbd one meter complete.')
        self._one_meter_stbd_complete = True

    # ..........................................................................
    def is_one_metering(self):
        return not self._one_meter_port_complete and not self._one_meter_stbd_complete


    # ==========================================================================
    # roam .....................................................................

    # ..........................................................................
    def _roam_callback_port(self):
        self._log.info(Fore.RED   + 'port roam complete.')
        self._roam_port_complete = True

    # ..........................................................................
    def _roam_callback_stbd(self):
        self._log.info(Fore.GREEN + 'stbd roam complete.')
        self._roam_stbd_complete = True

    # ..........................................................................
    def is_roaming(self):
        return not self._roam_port_complete and not self._roam_stbd_complete

    def _roam(self, pid, velocity, steps, orientation, callback):
        '''
           Thread method for each PID controller.
        '''
        _current_steps = pid.steps
        _target_steps = _current_steps + steps
        self._log.info(Fore.YELLOW + 'begin {} roaming from {:d} to {:d} steps.'.format(orientation.label, _current_steps, _target_steps))
        pid.velocity = velocity
        while pid.steps < _target_steps:
            # TODO accelerate
            # TODO cruise
            time.sleep(0.01)
        # TODO decelerate
        pid.velocity = 0.0

        callback()
        time.sleep(1.0)
        self._log.info('{} roaming complete: {:d} of {:d} steps.'.format(orientation.label, pid.steps, _target_steps))

    def roam(self):
        '''
           A pseudo-roam behaviour.
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
        self._log.info('roam.')
        self._roam_port_complete = False
        self._roam_stbd_complete = False
        _port_current_velocity = 0.0
        self._port_pid
        self._stbd_pid

        _forward_steps_per_rotation = 494
        _rotations = 5
        _forward_steps = _forward_steps_per_rotation * _rotations
        _velocity = 35.0 #Velocity.HALF
        self._log.info('start roaming at velocity {:5.2f} for {:d} steps'.format(_velocity, _forward_steps))

        _tp = threading.Thread(target=self._roam, args=(self._port_pid, _velocity, _forward_steps, Orientation.PORT, self._roam_callback_port))
        _ts = threading.Thread(target=self._roam, args=(self._stbd_pid, _velocity, _forward_steps, Orientation.STBD, self._roam_callback_stbd))
        _tp.start()
        _ts.start()
        _tp.join()
        _ts.join()
        self._log.info('complete.')
        pass


    # avoid ....................................................................
    def avoid(self, orientation):
        '''
            Avoids differently depending on orientation.           
        '''
        self._log.info(Fore.CYAN + 'avoid {}.'.format(orientation.name))
        
#        if orientation is Orientation.CNTR:
#            orientation = Orientation.PORT if random.choice((True, False)) else Orientation.STBD
#            self._log.info(Fore.YELLOW + 'randomly avoiding to {}.'.format(orientation.name))
#
#        self._ifs.suppress(True)
#        self._motors.halt()
#        self.back_up(0.5)
#        if orientation is Orientation.PORT:
#            self._motors.spin_port(self._fast_speed)
#        elif orientation is Orientation.STBD:
#            self._motors.spin_starboard(self._fast_speed)
#        else:
#            raise Exception('unexpected center orientation.')
#        time.sleep(2.0)
#        self._motors.brake()
#        self._ifs.suppress(False)

        self._log.info('action complete: avoid.')

    # sniff ....................................................................
    def sniff(self):
        if self._rgbmatrix.is_disabled():
            self._rgbmatrix.set_solid_color(Color.BLUE)
            self._rgbmatrix.set_display_type(DisplayType.SOLID)
#           self._rgbmatrix.set_display_type(DisplayType.RANDOM)
            self._rgbmatrix.enable()
        else:
            self._rgbmatrix.disable()

#EOF
