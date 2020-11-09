#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# Copyright 2020 by Murray Altheim. All rights reserved. This file is part of
# the Robot OS project and is released under the "Apache Licence, Version 2.0".
# Please see the LICENSE file included as part of this package.
#

from datetime import datetime as dt
from colorama import init, Fore, Style
init()

from lib.logger import Level, Logger
from lib.event import Event

class CruiseBehaviour():
    '''
        This class is added as a message consumer, and pays attention only to
        center IR sensor messages, adjusting the maximum velocity of the PID
        controller as a function of distance to a perceived obstacle.
    '''
    def __init__(self, config, pid_motor_controller, ifs, level):
        self._log = Logger("cruise", level)
        if config is None:
            raise ValueError('null configuration argument.')
        _config = config['ros'].get('cruise_behaviour')
        self._active_range_cm   = _config.get('active_range_cm')
        self._log.info('active range: {:5.2f}cm'.format(self._active_range_cm))
        self._cruising_velocity = _config.get('cruising_velocity') 
        self._log.info('cruising velocity: {:5.2f}cm'.format(self._cruising_velocity))
        self._pid_motor_ctrl    = pid_motor_controller
        _pid_controllers        = pid_motor_controller.get_pid_controllers()
        self._port_pid          = _pid_controllers[0]
        self._stbd_pid          = _pid_controllers[1]
        self._timeout_count     = 0
        self._timeout_limit     = 4
        self._enabled           = False
        self._log.info('ready.')

    # ..........................................................................
    def get_cruising_velocity(self):
        return self._cruising_velocity

    # ..........................................................................
    def set_max_velocity(self, velocity):
        if velocity is None:
            self._log.info(Fore.MAGENTA + 'setting MAXIMUM cruise velocity: NONE')
        else:
            self._log.info(Fore.MAGENTA + Style.BRIGHT + 'setting MAXIMUM cruise velocity: {:5.2f}'.format(velocity))
        self._pid_motor_ctrl.set_max_velocity(velocity)

    # ..........................................................................
    def set_cruising_velocity(self, velocity):
        self._log.info(Fore.MAGENTA + Style.BRIGHT + 'setting cruise velocity: {:5.2f}'.format(velocity))
        self._port_pid.velocity = velocity
        self._stbd_pid.velocity = velocity

  # ......................................................
    def add(self, message):
        '''
           If enabled, this listens for the 'tock' message and sets the forward
           velocity to the cruise velocity, with a normal slew rate so that the
           robot accelerates to that velocity within a reasonable period.

           This reacts to center IR events by setting the maximum forward 
           velocity of the PID controllers in proportion to the sensed distance,
           so that as the robot approaches an obstacle it will slow down, 
           ultimately stopping at about 20cm from it.

           If the distance exceeds a given limit the limit on the PID controller
           is removed.
        '''
        if not self._enabled:
            return
        event = message.event
#       self._log.info(Fore.WHITE + Style.BRIGHT + 'EVENT RECEIVED: {};\tvalue: {:5.2f}cm'.format(event.description, message.value))

#       if event is Event.CLOCK_TICK:
#           pass
        if event is Event.CLOCK_TOCK:
            # if enough time has passed since there's been an IR event, set the max velocity to None
            if self._timeout_count <= 0:
                self.set_cruising_velocity(self._cruising_velocity)
                self.set_max_velocity(None)
                self._log.info(Fore.GREEN + Style.NORMAL + 'TOCK RECEIVED;\tcount: {:5.2f};\ttimeout count: {:d}'.format(message.value, self._timeout_count) + Fore.RED + Style.NORMAL + '\tRESET MAX VELOCITY')
            else:
                # timeout count down
                self._timeout_count -= 1
                self._log.info(Fore.GREEN + Style.NORMAL + 'TOCK RECEIVED;\tcount: {:5.2f};\ttimeout count: {:d}'.format(message.value, self._timeout_count))
#               self.set_cruising_velocity(self._cruising_velocity)

        elif event is Event.INFRARED_CNTR:
            self._log.info(Fore.BLUE + 'INFRARED_CNTR RECEIVED;\tvalue: {:5.2f}cm'.format(message.value))
            _mean_distance = message.value
            if _mean_distance <= self._active_range_cm:
                _clamped_distance = CruiseBehaviour.clamp(_mean_distance, 20.0, self._active_range_cm)
                _mapped_velocity = CruiseBehaviour.remap(_clamped_distance, 20.0, 100.0, 0.0, self._cruising_velocity)
                self.set_max_velocity(_mapped_velocity)
                self.set_cruising_velocity(self._cruising_velocity)
                self._timeout_count = self._timeout_limit
                self._log.info(Fore.BLUE + Style.BRIGHT   + 'center sensor mean distance: {:5.2f}cm; setting max velocity: {:5.2f}'.format(_mean_distance, _mapped_velocity) \
                        + Fore.YELLOW + Style.NORMAL + '; timeout count: {:d}'.format(self._timeout_count))

            else: # out of range
                self._log.info(Fore.GREEN + 'center sensor mean distance: {:5.2f}cm; OUT OF RANGE.'.format(_mean_distance))
                self.set_cruising_velocity(self._cruising_velocity)

#       elif event is Event.INFRARED_PORT_SIDE:
#           self._log.debug(Fore.RED + Style.BRIGHT   + 'event: {};\tvalue: {:5.2f}cm'.format(event.description, message.value))
#       elif event is Event.INFRARED_PORT:
#           self._log.debug(Fore.RED + Style.BRIGHT   + 'event: {};\tvalue: {:5.2f}cm'.format(event.description, message.value))
#       elif event is Event.INFRARED_STBD:
#           self._log.debug(Fore.GREEN + Style.BRIGHT + 'event: {};\tvalue: {:5.2f}cm'.format(event.description, message.value))
#       elif event is Event.INFRARED_STBD_SIDE:
#           self._log.debug(Fore.GREEN + Style.BRIGHT + 'event: {};\tvalue: {:5.2f}cm'.format(event.description, message.value))
        else:
            pass

    # ..........................................................................
    def disable(self):
        if self._enabled:
            self._enabled = False
            self.set_cruising_velocity(0.0)
            self.set_max_velocity(None)
            self._log.info('disabled.')
        else:
            self._log.warning('already disabled.')

    # ..........................................................................
    def enable(self):
        '''
           A behaviour that drives forward with a cruising speed dictated
           by how close the center IR sensor is to an obstacle.
        '''
        self._enabled = True
        self.set_cruising_velocity(self._cruising_velocity)
        if not self._port_pid.enabled:
            self._port_pid.enable()
            self._stbd_pid.enable()
        self._log.info(Fore.GREEN + Style.BRIGHT + 'enable cruise at velocity: {:5.2f}'.format(self._cruising_velocity))

#   # ..........................................................................
#   def close(self):
#       self.disable()
#       self._log.info('closed.')
#       pass

    # ..........................................................................
    @staticmethod
    def clamp(n, minn, maxn):
        return max(min(maxn, n), minn)


   # ..........................................................................
    @staticmethod
    def remap(x, in_min, in_max, out_min, out_max):
        return (x - in_min) * (out_max - out_min) / (in_max - in_min) + out_min

#EOF
