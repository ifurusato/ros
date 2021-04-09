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
        self.events = [ Event.DECREASE_SPEED, Event.INCREASE_SPEED, Event.HALT, Event.STOP, Event.BRAKE ]
#       self._log = Logger('motors', level)
        self._log.info('initialising motors...')
        if config is None:
            raise Exception('no config argument provided.')
        self._config = config
        # config pigpio's pi and name its callback thread (ex-API)

        _tb = tb
        _pi = pi
        self._port_motor = Motor(self._config, ticker, _tb, _pi, Orientation.PORT, level)
        self._stbd_motor = Motor(self._config, ticker, _tb, _pi, Orientation.STBD, level)

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

    # ................................................................
    async def process_message(self, message, event):
        '''
        Process the message, i.e., do something with it to change the state of the robot.

        :param message:  the message to process, with its contained Event type.
        :param event:    the asyncio.Event to watch for message extention or cleaning up,
                         notably not the robot Event.
        '''
        while not event.is_set():
            message.process()
            _elapsed_ms = (dt.now() - message.timestamp).total_seconds() * 1000.0
            if self._message_bus.verbose:
                self._log.info(self._color + Style.BRIGHT + 'processing message: {} (event: {}) in {:5.2f}ms'.format(message.name, message.event.description, _elapsed_ms))
            # switch on event type...
            _event = message.event
            if _event == Event.STOP:
                self._log.info(self._color + Style.BRIGHT + 'event: STOP in {:5.2f}ms'.format(_elapsed_ms))
            elif _event == Event.HALT:
                self._log.info(self._color + Style.BRIGHT + 'event: HALT in {:5.2f}ms'.format(_elapsed_ms))
            elif _event == Event.BRAKE:
                self._log.info(self._color + Style.BRIGHT + 'event: BRAKE in {:5.2f}ms'.format(_elapsed_ms))
            elif _event == Event.INCREASE_SPEED:
                self._log.info(self._color + Style.BRIGHT + 'event: INCREASE_SPEED in {:5.2f}ms'.format(_elapsed_ms))
            elif _event == Event.DECREASE_SPEED:
                self._log.info(self._color + Style.BRIGHT + 'event: DECREASE_SPEED in {:5.2f}ms'.format(_elapsed_ms))
            elif _event == Event.AHEAD:
                self._log.info(self._color + Style.BRIGHT + 'event: AHEAD in {:5.2f}ms'.format(_elapsed_ms))
            elif _event == Event.ASTERN:
                self._log.info(self._color + Style.BRIGHT + 'event: ASTERN in {:5.2f}ms'.format(_elapsed_ms))
            else:
                self._log.info(self._color + Style.BRIGHT + 'ignored message: {} (event: {}) in {:5.2f}ms'.format(message.name, message.event.description, _elapsed_ms))

            # want to sleep for less than the deadline amount
            await asyncio.sleep(2)

    # ................................................................
    async def cleanup_message(self, message, event):
        '''
        Cleanup tasks related to completing work on a message.

        :param message:  consumed message that is done being processed.
        :param event:    the asyncio.Event to watch for message extention or cleaning up.
        '''
        # this will block until `event.set` is called
        await event.wait()
        # unhelpful simulation of i/o work
        await asyncio.sleep(random.random())
        message.expire()
        if self._message_bus.verbose:
            self._log.info(self._color + Style.DIM + 'cleanup done: acknowledged {}'.format(message.name))



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
