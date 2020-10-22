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

# from gpiozero import DigitalInputDevice
try:
    from gpiozero import DigitalInputDevice
    print('import            :' + Fore.CYAN + ' INFO  : successfully imported gpiozero DigitalInputDevice.' + Style.RESET_ALL)
except ImportError:
    print('import            :' + Fore.RED + ' ERROR : failed to import gpiozero DigitalInputDevice, using mock...' + Style.RESET_ALL)
    # from .import_gpio import DigitalInputDevice
    from .mock_gpiozero import DigitalInputDevice
except Exception:
    print('import            :' + Fore.RED + ' ERROR : failed to instantiate gpiozero DigitalInputDevice, using mock...' + Style.RESET_ALL)
    # from .import_gpio import DigitalInputDevice
    from .mock_gpiozero import DigitalInputDevice

from .logger import Logger, Level
from .devnull import DevNull

# the length of time that the sensor will ignore changes in state after an initial change
BOUNCE_TIME_SEC = None
# how long we wait to deactivate after being activated
DEACTIVATE_TIMEOUT_SEC = 1.0
# how long we wait to activate after being deactivated
ACTIVATE_TIMEOUT_SEC = 1.0


# ..............................................................................
class Bumper():
    '''
        Bumper Task: reacts to bumper sensors.
        
        Parameters:
    
           pin: the GPIO pin used as an input
           label: the label used in logging
           level: the logging Level
           activated_callback: a callback function called when the sensor is activated
           deactivated_callback: a callback function called when the sensor is deactivated
    
        Returns: 
    
            true for 1 second duration after a positive sensor reading.
    
        Usage:
    
           PIN = 25
           LABEL = 'center'
           LEVEL = Level.INFO
           _activated_callback = self.activated_callback
           _deactivated_callback = self.deactivated_callback
    
           _bumper = Bumper(PIN, LABEL, LEVEL, _activated_callback, _deactivated_callback)
           _bumper.enable()
           value = _bumper.get()
    '''

    def __init__(self, pin, label, level, activated_callback, deactivated_callback):
        '''
            The parameters include two optional callback functions, one when 
            the bumper is activated, another when deactivated. 
        '''
        self._log = Logger("bumper:" + label, level)
        self._log.debug('initialising bumper:{} on pin {}...'.format(label, pin))
        self._enabled = False
        if activated_callback is None:
            self._log.error("no activated_callback argument provided.")
        if deactivated_callback is None:
            self._log.error("no deactivated_callback argument provided.")
        self._pin = pin
        self._label = label
        self._sensor = DigitalInputDevice(pin, bounce_time=BOUNCE_TIME_SEC, pull_up=True)
        self._activated_callback = activated_callback
        self._deactivated_callback = deactivated_callback
        self._sensor.when_activated = self._activated
        self._sensor.when_deactivated = self._deactivated
        self._wait_for_inactive = True
        self._log.info('bumper on pin {} ready.'.format(label, pin))

    # ..........................................................................
    def set_wait_for_inactive(self, state):
        self._log.info('set wait for inactive for bumper:{} to: {}'.format(self._label, state))
        self._wait_for_inactive = state

    # ..........................................................................
    def enable(self):
        self._enabled = True
        self._log.info('enabled.')

    # ..........................................................................
    def disable(self):
        self._enabled = False
        self._log.info('disabled.')

    # ..........................................................................
    def poll(self):
        _active = self._sensor.is_active
        self._log.info('poll {} bumper: {}'.format(self._label, _active))
        return _active

    # ..........................................................................
    def _activated(self):
        '''
            The default function called when the sensor is activated.
        '''
        self._log.info('>> activated bumper:{} on pin {}...'.format(self._label, self._pin))
        if self._enabled:
            if self._activated_callback != None:
                self._log.info('calling activated_callback...')
                # Pause the script until the device is deactivated, or the timeout is reached.
                #     Parameters:	timeout (float or None) – Number of seconds to wait before proceeding. 
                #                       If this is None (the default), then wait indefinitely until the device is inactive.
#               self._log.info('wait for inactive: bumper:{} on pin {}.'.format(self._label,self._pin))
                if self._wait_for_inactive:
                    self._sensor.wait_for_inactive(timeout=ACTIVATE_TIMEOUT_SEC)
#               self._sensor.wait_for_inactive(timeout=None)
                self._activated_callback()
            else:
                self._log.warning('activated_callback is None!')
        else:
            self._log.warning('[DISABLED] activated bumper:{} on pin {}...'.format(self._label, self._pin))

    # ..........................................................................
    def _deactivated(self):
        '''
            The default function called when the sensor is deactivated.
        '''
        self._log.debug('>> deactivated bumper:{} on pin {}...'.format(self._label, self._pin))
        if self._enabled:
            if self._deactivated_callback != None:
                self._log.debug('calling deactivated_callback...')
                # Pause the script until the device is activated, or the timeout is reached.
                #     Parameters:	timeout (float or None) – Number of seconds to wait before proceeding. 
                #                       If this is None (the default), then wait indefinitely until the device is active.
#               self._log.info('wait for active: bumper:{} on pin {}.'.format(self._label,self._pin))
                self._sensor.wait_for_active(timeout=DEACTIVATE_TIMEOUT_SEC)
#               self._sensor.wait_for_active(timeout=None)
                self._deactivated_callback() 
            else:
                self._log.warning('deactivated_callback is None!')

        else:
            self._log.warning('[DISABLED] deactivated bumper:{} on pin {}...'.format(self._label, self._pin))

    # ..........................................................................
    def close(self):
        self._log.info('closed.')

# EOF
