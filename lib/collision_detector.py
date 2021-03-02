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
    from gpiozero import DigitalInputDevice
    print('successfully imported gpiozero.')
except Exception:
    print('unable to import gpiozero.')

from lib.logger import Logger, Level
from lib.event import Event
from lib.message import Message

# ..............................................................................
class CollisionDetector():
    '''
    Uses an 15cm infrared sensor to scan for an imminent collision at the front
    of the robot, particularly with the mast. This class may be extended to
    include multiple sensors that send the same COLLISION_DETECT message.
    '''
    def __init__(self, config, message_factory, message_bus, level):
        self._log = Logger('collision', Level.INFO)
        if config is None:
            raise ValueError('no configuration provided.')
        self._message_factory = message_factory
        self._message_bus = message_bus
        _config = config['ros'].get('collision_detect')
        _pin    = _config.get('pin')
        self._sensor = DigitalInputDevice(_pin, bounce_time=0.2, pull_up=False)
        self._sensor.when_activated   = self._activated
        self._sensor.when_deactivated = self._deactivated
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
            self._log.info(Fore.YELLOW + 'detected mast sensor!')
            self._message_bus.handle(self._message_factory.get_message(Event.COLLISION_DETECT, True))
        else:
            self._log.info('collision detection not enabled.')

    # ..........................................................................
    def _deactivated(self):
        '''
        The default function called when the sensor is deactivated.
        '''
        if self._enabled:
            self._log.info('deactivated collision detection.')
        else:
            self._log.debug('collision detection not enabled.')

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
