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

#from gpiozero import MotionSensor
try:
    from gpiozero import MotionSensor
    print('import            :' + Fore.BLACK + ' INFO  : successfully imported gpiozero MotionSensor.' + Style.RESET_ALL)
#except ImportError:
#    print('import            :' + Fore.RED + ' ERROR : failed to import gpiozero MotionSensor, using mock...' + Style.RESET_ALL)
#    # from .import_gpio import MotionSensor
#    from .mock_gpiozero import MotionSensor
except Exception:
#   print('import            :' + Fore.RED + ' ERROR : error importing gpiozero MotionSensor, using mock...' + Style.RESET_ALL)
    # from .import_gpio import MotionSensor
#    from .mock_gpiozero import MotionSensor
    print('import            :' + Fore.RED + ' ERROR : unable to import gpiozero MotionSensor, exiting...' + Style.RESET_ALL)
    sys.exit(1)

from lib.logger import Logger, Level
from lib.devnull import DevNull
from lib.enums import Orientation
from lib.event import Event
from lib.message import Message

# ..............................................................................
class Infrared():
    '''
        Infrared Task: reacts to infrared sensors.
        
        Parameters:
    
           pin: the GPIO pin used as an input
           event: the Event to be sent when the sensor is activated
           queue: the message queue receiving activation notifications
           level: the logging Level
    
        Usage:
    
           PIN = 12
           _infrared = Infrared(_queue, PIN, Orientation.PORT, Event.INFRARED_PORT, Level.INFO)
           _infrared.enable()

    '''

    THRESHOLD_VALUE = 0.1          # the value above which the device will be considered “on”
    DEACTIVATE_TIMEOUT_SEC = 0.01   # how long we wait to deactivate after being activated. If None (the default) then wait indefinitely.
#   DEACTIVATE_TIMEOUT_SEC = None 
    ACTIVATE_TIMEOUT_SEC   = 0.2    # | 1.0 how long we wait to activate after being deactivated. If None (the default) then wait indefinitely.
#   ACTIVATE_TIMEOUT_SEC   = None

    # ..........................................................................
    def __init__(self, queue, pin, orientation, event, level):
        self._queue = queue
        self._pin = pin
        self._orientation = orientation
        self._event = event
        self._label = event.description
        self._log = Logger("infrared:" + self._orientation.label, level)
        self._log.debug('initialising {} infrared:{} on pin {}.'.format(orientation.label, self._label,pin))

        self._closed = False
        self._enabled = False
        self._sensor = MotionSensor(pin, threshold=Infrared.THRESHOLD_VALUE, pull_up=True)
        self._sensor.when_motion    = self._activated
        self._sensor.when_no_motion = self._deactivated
        self._log.info('ready.')


    # ..........................................................................
    def enable(self):
        if not self._closed:
            self._log.info('enabled infrared:{}'.format(self._label))
            self._enabled = True
        else:
            self._log.warning('cannot enable infrared:{} (closed)'.format(self._label))


    # ..........................................................................
    def disable(self):
        self._log.info('disabled infrared:{}'.format(self._label))
        self._enabled = False


    # ..........................................................................
    def _activated(self):
        '''
            The default function called when the sensor is activated.
        '''
        if self._enabled:
            if self._orientation is Orientation.PORT or self._orientation is Orientation.PORT_SIDE:
                self._log.info(Fore.RED + 'activated {} infrared:{} on pin {}...'.format(self._orientation.label, self._label, self._pin))
            elif self._orientation is Orientation.STBD or self._orientation is Orientation.STBD_SIDE:
                self._log.info(Fore.GREEN + 'activated {} infrared:{} on pin {}...'.format(self._orientation.label, self._label, self._pin))
            else:
                self._log.info(Fore.YELLOW + 'activated {} infrared:{} on pin {}...'.format(self._orientation.label, self._label, self._pin))
            self._queue.add(Message(self._event))
            if Infrared.ACTIVATE_TIMEOUT_SEC:
                self._sensor.wait_for_inactive(timeout=Infrared.ACTIVATE_TIMEOUT_SEC)
        else:
            self._log.info('[DISABLED] activated infrared:{} on pin {}...'.format(self._label,self._pin))


    # ..........................................................................
    def _deactivated(self):
        '''
            The default function called when the sensor is deactivated.
        '''
        if self._enabled:
            self._log.debug(Style.DIM + 'deactivated {} infrared:{} on pin {}...'.format(self._orientation.label, self._label, self._pin) + Style.RESET_ALL)
            if Infrared.DEACTIVATE_TIMEOUT_SEC:
                self._sensor.wait_for_active(timeout=Infrared.DEACTIVATE_TIMEOUT_SEC)
        else:
            self._log.debug('[DISABLED] deactivated infrared:{} on pin {}...'.format(self._label,self._pin))


    # ..........................................................................
    def close(self):
        '''
            Permanently close and disable the infrared sensor.
        '''
        self._closed = True
        self._enabled = False
        self._log.info('closed.')


#EOF
