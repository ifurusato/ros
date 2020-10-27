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
from lib.event import Event
from lib.rgbmatrix import RgbMatrix, Color, DisplayType
from lib.pid_v4 import PIDController
from lib.slew import SlewRate
from lib.geometry import Geometry
from lib.rate import Rate

class CruiseBehaviour():
    '''
        This class is added as a message consumer, and pays attention only to
        center IR sensor messages, adjusting the maximum velocity of the PID
        controller as a function of distance to a perceived obstacle.
    '''
    def __init__(self, config, pid_motor_controller, ifs, level):
        self._log = Logger("behave", level)
        if config is None:
            raise ValueError('null configuration argument.')
        self._geo = Geometry(config, level)
        _config = config['ros'].get('cruise_behaviour')
        self._accel_range_cm     = _config.get('accel_range_cm')
        self._cruising_velocity  = _config.get('cruising_velocity') 
        self._ifs = ifs
        self._pid_motor_ctrl = pid_motor_controller
        _pid_controllers = pid_motor_controller.get_pid_controllers()
        self._port_pid = _pid_controllers[0]
        self._stbd_pid = _pid_controllers[1]
        self._rgbmatrix = RgbMatrix(Level.INFO)
        self._fast_speed = 99.0
        self._slow_speed = 50.0
        self._cruise_enable      = False
        self._port_cruise_thread = None
        self._stbd_cruise_thread = None
        self._log.info('ready.')

    # ..........................................................................
    def get_cruising_velocity(self):
        return self._cruising_velocity

    # ..........................................................................
    def adjust_cruise(self, velocity):
        self._pid_motor_ctrl.set_max_velocity(_mapped_velocity)

  # ......................................................
    def add(self, message):

        event = message.event
        if event is Event.INFRARED_PORT_SIDE:
            self._log.debug(Fore.RED + Style.BRIGHT   + 'event: {};\tvalue: {:5.2f}cm'.format(event.description, message.value))
        elif event is Event.INFRARED_PORT:
            self._log.debug(Fore.RED + Style.BRIGHT   + 'event: {};\tvalue: {:5.2f}cm'.format(event.description, message.value))

        elif event is Event.INFRARED_CNTR:
            _mean_distance = message.value
            self._log.info(Fore.MAGENTA + Style.BRIGHT   + 'center sensor mean distance: {:5.2f}cm'.format(message.value))
            _clamped_distance = CruiseBehaviour.clamp(_mean_distance, 20.0, 100.0)
            _mapped_velocity = CruiseBehaviour.remap(_clamped_distance, 20.0, 100.0, 0.0, self._cruising_velocity)
            self._pid_motor_ctrl.set_max_velocity(_mapped_velocity)

#       elif event is Event.INFRARED_CNTR:
#           _cruising_velocity = self._behaviours.get_cruising_velocity()
#           _distance = message.value
#           _clamped_distance = Behaviours.clamp(_distance, 20.0, 100.0)
#           _mapped_velocity = Behaviours.remap(_clamped_distance, 20.0, 100.0, 0.0, _cruising_velocity)
#           self._log.info(Fore.BLUE + Style.NORMAL  + 'event: {};'.format(event.description) + Fore.YELLOW + '\tmapped velocity: {:5.2f}cm'.format(message.value ))
#           self._log.info(Fore.BLUE + Style.NORMAL + '_distance: {:5.2f}\t'.format(_distance) + Style.BRIGHT + '\tcruising velocity: {:5.2f}cm;'.format(_cruising_velocity) \
#                   + Fore.YELLOW + Style.NORMAL + '\tvelocity: {:5.2f}'.format(_mapped_velocity))
#           pids = self._pid_motor_ctrl.set_max_velocity(_mapped_velocity)

        elif event is Event.INFRARED_STBD:
            self._log.debug(Fore.GREEN + Style.BRIGHT + 'event: {};\tvalue: {:5.2f}cm'.format(event.description, message.value))
        elif event is Event.INFRARED_STBD_SIDE:
            self._log.debug(Fore.GREEN + Style.BRIGHT + 'event: {};\tvalue: {:5.2f}cm'.format(event.description, message.value))
        else:
            pass


    # cruise ...................................................................
    def cruise(self):
        '''
           A behaviour that drives forward with a cruising speed dictated
           by how close the center IR sensor is to an obstacle.
        '''
        if self._cruise_enable:
            self._log.info(Fore.MAGENTA + Style.BRIGHT + 'setting cruise FALSE     ░░░░░░░░░░░░░░░░░░░░░░░░ ')
#           self._log.info('cruise already running: stopping...')
            # then exit loop
            self._cruise_enable = False
            self._port_cruise_thread = None
            self._stbd_cruise_thread = None

        else:
            self._log.info(Fore.MAGENTA + Style.BRIGHT + 'setting cruise TRUE      █████████████████████████ ')
            if self._port_cruise_thread or self._stbd_cruise_thread:
                raise Exception('can\'t start cruise: threads still exist.')
            self._cruise_enable = True
            self._port_cruise_thread = threading.Thread(target=CruiseBehaviour._cruise, args=[self, self._port_pid, lambda: self._cruise_enable ])
            self._stbd_cruise_thread = threading.Thread(target=CruiseBehaviour._cruise, args=[self, self._stbd_pid, lambda: self._cruise_enable ])
            self._port_cruise_thread.start()
            self._stbd_cruise_thread.start()
            self._port_cruise_thread.join()
            self._stbd_cruise_thread.join()
            self._log.info(Fore.WHITE + Style.BRIGHT + 'cruise thread joined.               ████  ████  ████ ')
            
            for i in range(10):
                self._log.info(Fore.WHITE + 'i = {:d}'.format(i))
                time.sleep(1)
            self._cruise_enable  = False
            self._log.info('cruise complete.')

    def _cruise(self, pid, f_is_enabled):
        '''
           Threaded method for cruise.
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
        
        # accelerate to cruising velocity ............................................
#       self._rgbmatrix.show_color(Color.CYAN, Orientation.STBD)
        self._log.info(Fore.YELLOW + '{} motor accelerating...'.format(pid.orientation.label))
        while pid.steps < _accel_target_steps:
            pid.velocity = self._cruising_velocity
            _rate.wait()
     
        # cruise until 3/4 of range ..................................................
        self._log.info(Fore.YELLOW + '{} motor reached cruising velocity...'.format(pid.orientation.label))
        pid.velocity = self._cruising_velocity

        while f_is_enabled:
            self._log.info(Fore.MAGENTA + Style.NORMAL + '{:d} cruise looping...; velocity: {}'.format(pid.steps, pid.velocity))

#           _distance = self._ifs.get_mean_distance(Orientation.CNTR)
#           _clamped_distance = Behaviours.clamp(_distance, 20.0, 100.0)
#           _mapped_velocity = Behaviours.remap(_clamped_distance, 20.0, 100.0, 0.0, self._cruising_velocity)
#           self._log.info(Fore.MAGENTA + Style.NORMAL + '{:d}\t'.format(pid.steps) + Style.BRIGHT + 'distance: {:5.2f}cm;'.format(_distance) + Fore.YELLOW + Style.NORMAL + '\tvelocity: {:5.2f}'.format(_mapped_velocity))
#           pid.set_max_velocity(_mapped_velocity)

#           self._ifs.get_mean_distance(orientation, value)

            time.sleep(1.0)

        self._log.info(Fore.YELLOW + '{} motor stopping...'.format(pid.orientation.label))
        while pid.velocity > 0.0:
            pid.velocity -= 0.1
            self._log.info(Fore.YELLOW + Style.DIM + '{:d} stopping...; velocity: {}'.format(pid.steps, pid.velocity))
            time.sleep(0.01)

        _motors = pid.reset() # reset PID and stop motor
    
        time.sleep(1.0)
        pid.set_slew_rate(SlewRate.NORMAL)

        self._log.info(Fore.YELLOW + 'executing {} callback...'.format(pid.orientation.label))
        self._rgbmatrix.disable()
#       pid.reset()
#       pid.disable()
        self._log.info(Fore.YELLOW + 'one meter on {} motor complete: {:d} of {:d} steps.'.format(pid.orientation.label, pid.steps, _target_steps))

    # ..........................................................................
    def close(self):
        self._log.info('closed.')
        pass

    # ..........................................................................
    @staticmethod
    def clamp(n, minn, maxn):
        return max(min(maxn, n), minn)


   # ..........................................................................
    @staticmethod
    def remap(x, in_min, in_max, out_min, out_max):
        return (x - in_min) * (out_max - out_min) / (in_max - in_min) + out_min

#EOF
