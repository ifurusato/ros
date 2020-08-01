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
        self._port_side_trigger_distance = self._config.get('port_side_trigger_distance')
        self._port_trigger_distance      = self._config.get('port_trigger_distance')
        self._center_trigger_distance    = self._config.get('center_trigger_distance')
        self._stbd_trigger_distance      = self._config.get('stbd_trigger_distance')
        self._stbd_side_trigger_distance = self._config.get('stbd_side_trigger_distance')
        self._log.info('event thresholds:' \
                + Fore.RED + ' port side={:>5.2f}; port={:>5.2f};'.format(self._port_side_trigger_distance, self._port_trigger_distance) \
                + Fore.BLUE + ' center={:>5.2f};'.format(self._center_trigger_distance) \
                + Fore.GREEN + ' stbd={:>5.2f}; stbd side={:>5.2f}'.format(self._stbd_trigger_distance, self._stbd_side_trigger_distance ))
        self._loop_delay_sec = self._config.get('loop_delay_sec')
        self._log.debug('initialising integrated front sensor...')
        self._master = I2cMaster(config, Level.INFO)
        self._enabled = False
        self._closed = False
        self._log.info('ready.')


    # ..........................................................................
    def _callback_front(self, pin, pin_type, value):
        '''
            This is the callback method from the I2C Master, whose events are
            being returned from the Arduino.

            The pin designations for each sensor here mirror those in the YAML 
            configuration. The default pins A1-A5 are defined as IR analog
            sensors, 9-11 are digital bumper sensors.
        '''
        self._log.debug(Fore.BLACK + Style.BRIGHT + 'callback: pin {:d}; type: {}; value: {:d}'.format(pin, pin_type, value))
        if not self._enabled:
            return
        _message = None
        if pin == 1:
            if value > self._stbd_side_trigger_distance:
                _message = Message(Event.INFRARED_STBD_SIDE)
        elif pin == 2:
            if value > self._stbd_trigger_distance:
                _message = Message(Event.INFRARED_STBD)
        elif pin == 3:
            if value > self._center_trigger_distance:
                _message = Message(Event.INFRARED_CENTER)
        elif pin == 4:
            if value > self._port_trigger_distance:
                _message = Message(Event.INFRARED_PORT)
        elif pin == 5:
            if value > self._port_side_trigger_distance:
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
            assignments = self._master.configure_front_sensor_loop()
            if assignments is not None:
                self._master.enable()
                if not self._master.in_loop():
                    self._master.start_front_sensor_loop(assignments, self._loop_delay_sec, self._callback_front)
            else:
                self._log.error('cannot start integrated front sensor.')
        else:
            self._log.warning('cannot enable integrated front sensor: already closed.')


    # ..........................................................................
    def disable(self):
        self._log.info('disabled integrated front sensor.')
        self._enabled = False
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
