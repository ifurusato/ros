#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# Copyright 2020 by Murray Altheim. All rights reserved. This file is part of
# the Robot OS project and is released under the "Apache Licence, Version 2.0".
# Please see the LICENSE file included as part of this package.
#
# author:   altheim
# created:  2020-01-18
# modified: 2020-02-06

import time, sys, threading
from colorama import init, Fore, Style
init()

from lib.logger import Logger, Level
from lib.i2c_master import I2cMaster
from lib.event import Event
from lib.message import Message

# ..............................................................................
class IntegratedFrontSensor():
    '''
        IntegratedFrontSensor: communicates with the integrated front bumpers 
           and infrared sensors, receiving messages from the I2C Arduino slave,
           sending the messages with its events onto the message bus.
        
        Parameters:
    
           config: the YAML based application configuration
           queue:  the message queue receiving activation notifications
           level:  the logging Level
    
        Usage:
    
           _ifs = IntegratedFrontSensor(_config, _queue, Level.INFO)
           _ifs.enable()

    '''

    # ..........................................................................
    def __init__(self, config, queue, level):
        if config is None:
            raise ValueError('no configuration provided.')
        self._config = config['ros'].get('front_sensor')
        self._queue = queue
        self._log = Logger("front-sensor", level)
        self._trigger_distance = self._config.get('trigger_distance')
        self._loop_delay_sec = self._config.get('loop_delay_sec')
        self._log.debug('initialising integrated front sensor...')

        self._master = I2cMaster(config, Level.INFO)
        self._closed = False
        self._enabled = False
        self._log.info('ready.')


    # ..........................................................................
    def _callback_front(self, pin, pin_type, value):
        '''
            This is the callback method from the I2C Master, whose events are
            being returned from the Arduino.

            The pin designations for each sensor here mirror those in the YAML 
            configuration.
        '''
        self._log.debug(Fore.BLACK + Style.BRIGHT + 'callback: pin {:d}; type: {}; value: {:d}'.format(pin, pin_type, value))
        _message = None
        if pin == 0:
            if value > self._trigger_distance:
                _message = Message(Event.INFRARED_STBD_SIDE)
        elif pin == 1:
            if value > self._trigger_distance:
                _message = Message(Event.INFRARED_STBD)
        elif pin == 2:
            if value > self._trigger_distance:
                _message = Message(Event.INFRARED_CENTER)
        elif pin == 3:
            if value > self._trigger_distance:
                _message = Message(Event.INFRARED_PORT)
        elif pin == 4:
            if value > self._trigger_distance:
                _message = Message(Event.INFRARED_PORT_SIDE)
        elif pin == 9:
            if value == 1:
                _message = Message(Event.BUMPER_STBD)
        elif pin == 10:
            if value == 1:
                _message = Message(Event.BUMPER_CENTER)
        elif pin == 11:
            if value == 1:
                _message = Message(Event.BUMPER_PORT)

        if _message is not None:
            _message.set_value(value)
            self._queue.add(_message)


    # ..........................................................................
    def enable(self):
        if not self._closed:
            self._log.info('enabled integrated front sensor.')
            self._enabled = True
            self._master.front_sensor_loop(self._queue, self._enabled, self._loop_delay_sec, self._callback_front)
        else:
            self._log.warning('cannot enable integrated front sensor: already closed.')


    # ..........................................................................
    def disable(self):
        self._log.info('disabled integrated front sensor.')
        self._enabled = False
        if self._master:
            self._master.disable()


    # ..........................................................................
    def close(self):
        '''
            Permanently close and disable the integrated front sensor.
        '''
        self._closed = True
        self._enabled = False
        self._log.info('closed.')


#EOF
