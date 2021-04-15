#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# Copyright 2020 by Murray Altheim. All rights reserved. This file is part of
# the Robot OS project and is released under the "Apache Licence, Version 2.0".
# Please see the LICENSE file included as part of this package.
#
# author:   Murray Altheim
# created:  2021-02-16
# modified: 2021-02-16
#

import asyncio
import random
from datetime import datetime as dt
from colorama import init, Fore, Style
init()

from lib.logger import Logger, Level
from lib.enums import Orientation
from lib.event import Event
from lib.subscriber import Subscriber
from mock.motor import Motor

# ..............................................................................
class Motors(Subscriber):
    '''
    A mocked dual motor controller with encoders.

    :param name:         the subscriber name (for logging)
    :param ticker:       the clock providing a timing pulse to calculate velocity
    :param tb:           the ThunderBorg motor controller
    :param message_bus:  the message bus
    :param events:       the list of events used as a filter, None to set as cleanup task
    :param level:        the logging level 
    '''
    def __init__(self, config, ticker, tb, pi, message_bus, level=Level.INFO):
        super().__init__('motors', Fore.BLUE, message_bus, level)
        self._events = [ Event.DECREASE_SPEED, Event.INCREASE_SPEED, Event.HALT, Event.STOP, Event.BRAKE ]
        self._log.info('initialising motors...')
        if config is None:
            raise Exception('no config argument provided.')
        self._config = config
        # config pigpio's pi and name its callback thread (ex-API)

        if tb is None:
            raise Exception('no tb argument provided.')
        _tb = tb
        if pi is None:
            raise Exception('no pi argument provided.')
        self._pi = pi
        self._port_motor = Motor(self._config, ticker, _tb, self._pi, Orientation.PORT, level)
        self._stbd_motor = Motor(self._config, ticker, _tb, self._pi, Orientation.STBD, level)

        self._closed  = False
        self._enabled = False # used to be enabled by default
        # a dictionary of motor # to last set value
        self._last_set_power = { 0:0, 1:0 }
        self._log.info('motors ready.')

    # ..........................................................................
    @property
    def name(self):
        return 'motors'

    # ..........................................................................
    def get_motor(self, orientation):
        if orientation is Orientation.PORT:
            return self._port_motor
        else:
            return self._stbd_motor

    # ..........................................................................
    def change_speed(self, orientation, change):
        if orientation is Orientation.PORT:
            _port_power = self._port_motor.get_current_power_level()
            _updated_port_power = _port_power + change
            self._port_motor.set_motor_power(_updated_port_power)
            _port_power = self._port_motor.get_current_power_level()
            self._log.info(Fore.RED + Style.NORMAL + 'port motor power: {:5.2f} + {:5.2f} -▶ {:<5.2f}'.format(_port_power, change, _updated_port_power))
        else:
            _stbd_power = self._stbd_motor.get_current_power_level()
            _updated_stbd_power = _stbd_power + change
            self._stbd_motor.set_motor_power(_updated_stbd_power)
            _stbd_power = self._stbd_motor.get_current_power_level()
            self._log.info(Fore.GREEN + Style.NORMAL + 'stbd motor power: {:5.2f} + {:5.2f} -▶ {:<5.2f}'.format(_stbd_power, change, _updated_stbd_power))

    # ..........................................................................
    def halt(self):
        '''
        Quickly (but not immediately) stops both motors.
        '''
        self._log.info('halting...')
        if not self.is_stopped():
            self._port_motor.stop()
            self._stbd_motor.stop()
#           _tp = Thread(name='halt-port', target=self.processStop, args=(Event.HALT, Orientation.PORT))
#           _ts = Thread(name='hapt-stbd', target=self.processStop, args=(Event.HALT, Orientation.STBD))
#           _tp.start()
#           _ts.start()
            self._log.info('halted.')
        else:
            self._log.debug('already halted.')
        return True

    # ..........................................................................
    def brake(self):
        '''
        Slowly coasts both motors to a stop.
        '''
        self._log.info('braking...')
        if not self.is_stopped():
            self._port_motor.stop()
            self._stbd_motor.stop()
#           _tp = Thread(name='brake-port', target=self.processStop, args=(Event.BRAKE, Orientation.PORT))
#           _ts = Thread(name='brake-stbd', target=self.processStop, args=(Event.BRAKE, Orientation.STBD))
#           _tp.start()
#           _ts.start()
            self._log.info('braked.')
        else:
            self._log.warning('already braked.')
        return True

    # ..........................................................................
    def stop(self):
        '''
        Stops both motors immediately, with no slewing.
        '''
        self._log.info('stopping...')
        if not self.is_stopped():
            self._port_motor.stop()
            self._stbd_motor.stop()
            self._log.info('stopped.')
        else:
            self._log.warning('already stopped.')
        return True

    # ..........................................................................
    def is_stopped(self):
        return self._port_motor.is_stopped() and self._stbd_motor.is_stopped()

    # ..........................................................................
    def is_in_motion(self):
        '''
        Returns true if either motor is moving.
        '''
        return self._port_motor.is_in_motion() or self._stbd_motor.is_in_motion()

    # ................................................................
    async def process_message(self, message, event):
        '''
        Process the message, i.e., do something with it to change the state of the robot.

        :param message:  the message to process, with its contained Event type.
        :param event:    the asyncio.Event to watch for message extention or cleaning up,
                         notably not the robot Event.
        '''
#       while not event.is_set():
        while not event.is_set() and not message.gcd:
            if message.gcd:
                self._log.warning('exiting process loop: message {} has been garbage collected.'.format(message.name))
#               raise Exception('cannot process: message has been garbage collected.')
                return
            print('motors.process_message() 1. ---------------------------------- ')
            message.process(self)
            print('motors.process_message() 2. ---------------------------------- ')
            if self._message_bus.verbose:
                _elapsed_ms = (dt.now() - message.timestamp).total_seconds() * 1000.0
                self.print_message_info('processing message:', message, _elapsed_ms)
            # switch on event type...
            _event = message.event
            if _event == Event.STOP:
                self._log.info(self._color + Style.BRIGHT + 'event: STOP')
                self.stop()
            elif _event == Event.HALT:
                self._log.info(self._color + Style.BRIGHT + 'event: HALT')
                self.halt()
            elif _event == Event.BRAKE:
                self._log.info(self._color + Style.BRIGHT + 'event: BRAKE')
                self.brake()
            elif _event == Event.INCREASE_SPEED:
                self._log.info(self._color + Style.BRIGHT + 'event: INCREASE_SPEED')
                self.change_speed(Orientation.PORT, +0.01)
                self.change_speed(Orientation.STBD, +0.01)
            elif _event == Event.DECREASE_SPEED:
                self._log.info(self._color + Style.BRIGHT + 'event: DECREASE_SPEED')
                self.change_speed(Orientation.PORT, -0.01)
                self.change_speed(Orientation.STBD, -0.01)
            elif _event == Event.AHEAD:
                self._log.info(self._color + Style.BRIGHT + 'event: AHEAD')
            elif _event == Event.ASTERN:
                self._log.info(self._color + Style.BRIGHT + 'event: ASTERN')
            else:
                self._log.info(self._color + Style.BRIGHT + 'ignored message: {} (event: {})'.format(message.name, message.event.description))

            # want to sleep for less than the deadline amount
            await asyncio.sleep(2)

            if self._message_bus.verbose:
                _elapsed_ms = (dt.now() - message.timestamp).total_seconds() * 1000.0
                self.print_message_info('processing complete:', message, _elapsed_ms)

    # ................................................................
#   async def cleanup_message(self, message, event):
#       '''
#       Cleanup tasks related to completing work on a message.

#       :param message:  consumed message that is done being processed.
#       :param event:    the asyncio.Event to watch for message extention or cleaning up.
#       '''
#       # this will block until `event.set` is called
#       await event.wait()
#       # unhelpful simulation of i/o work
#       await asyncio.sleep(random.random())
#       message.expire()
#       if self._message_bus.verbose:
#           self._log.info(self._color + Style.DIM + 'cleanup done: acknowledged {}'.format(message.name))

    # ..........................................................................
    def enable(self):
        '''
        Enables the motors. This issues a warning if already enabled, but no
        harm is done in calling it repeatedly.
        '''
        if self._enabled:
            self._log.warning('already enabled.')
        if not self._port_motor.enabled:
            self._port_motor.enable()
        if not self._stbd_motor.enabled:
            self._stbd_motor.enable()
        self._enabled = True
        self._log.info('enabled.')

    # ..........................................................................
    def disable(self):
        '''
        Disable the motors, halting first if in motion.
        '''
        if self._enabled:
            self._log.info('disabling...')
            self._enabled = False
            if self.is_in_motion(): # if we're moving then halt
                self._log.warning('event: motors are in motion (halting).')
                self.halt()
            self._port_motor.disable()
            self._stbd_motor.disable()
            self._log.info('disabling pigpio...')
            self._pi.stop()
            self._log.info('disabled.')
        else:
            self._log.debug('already disabled.')

    # ..........................................................................
    def close(self):
        '''
        Halts, turn everything off and stop doing anything.
        '''
        if not self._closed:
            if self._enabled:
                self.disable()
            self._log.info('closing...')
            self._port_motor.close()
            self._stbd_motor.close()
            self._closed = True
            self._log.info('closed.')
        else:
            self._log.debug('already closed.')

    # ..........................................................................
    @staticmethod
    def cancel():
        print('cancelling motors...')
#       Motor.cancel()

#EOF
