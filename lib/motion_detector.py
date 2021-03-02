#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# Copyright 2020-2021 by Murray Altheim. All rights reserved. This file is part
# of the Robot Operating System project, released under the MIT License. Please
# see the LICENSE file included as part of this package.
#
# author:   altheim
# created:  2020-03-31
# modified: 2021-02-28
#

from colorama import init, Fore, Style
init()

try:
    from gpiozero import MotionSensor
    print('successfully imported gpiozero.')
except Exception:
    print('unable to import gpiozero.')

from lib.logger import Logger, Level
from lib.event import Event
from lib.message import Message


# ..............................................................................
class MotionDetector():
    '''
    Uses an infrared PIR sensor to scan for cats, or other causes of motion.
    '''
    def __init__(self, config, message_factory, message_bus, level):
        self._log = Logger('motion-detect', Level.INFO)
        if config is None:
            raise ValueError('no configuration provided.')
        self._message_factory = message_factory
        self._message_bus = message_bus
        _config = config['ros'].get('motion_detect')
        _pin    = _config.get('pin')

        _threshold_value = 0.1 # the value above which the device will be considered “on”
#       set up pin where PIR is connected
        self._sensor = MotionSensor(_pin, threshold=_threshold_value, pull_up=False)
        self._sensor.when_motion    = self._activated
        self._sensor.when_no_motion = self._deactivated
        self._disabling = False
        self._enabled = False
        self._closed = False
        # arm behaviour
        self._arm_movement_degree_step = 5.0
        self._arm_up_delay             = 0.09
        self._arm_down_delay           = 0.04
        self._log.info('ready.')

    # ..........................................................................
    def _activated(self):
        '''
        The default function called when the sensor is activated.
        '''
        if self._enabled:
            self._log.info(Fore.YELLOW + 'detected motion!')
            self._message_bus.handle(self._message_factory.get_message(Event.MOTION_DETECT, True))
        else:
            self._log.info('motion detector not enabled.')

    # ..........................................................................
    def _deactivated(self):
        '''
        The default function called when the sensor is deactivated.
        '''
        if self._enabled:
            self._log.info('deactivated motion detector.')
        else:
            self._log.debug('motion detector not enabled.')

    # ..........................................................................
    def enable(self):
        self._log.debug('enabling...')
        if self._closed:
            self._log.warning('cannot enable: closed.')
            return
        self._enabled = True
        self._log.debug('enabled.')

    # ..........................................................................
    def disable(self):
        if self._disabling:
            self._log.warning('already disabling.')
        else:
            self._disabling = True
            self._enabled = False
            self._log.debug('disabling...')
            self._disabling = False
            self._log.debug('disabled.')

    # ..........................................................................
    def close(self):
        self.disable()
        self._closed = True

#EOF
