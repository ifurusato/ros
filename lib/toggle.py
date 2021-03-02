#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# Copyright 2020-2021 by Murray Altheim. All rights reserved. This file is part
# of the Robot Operating System project, released under the MIT License. Please
# see the LICENSE file included as part of this package.
#
# author:   Murray Altheim
# created:  2021-02-14
# modified: 2021-02-14
#

import RPi.GPIO as GPIO
from colorama import init, Fore, Style
init()

from lib.logger import Level, Logger

# ..............................................................................
class Toggle(object):
    '''
    Returns a boolean value indicating the state of a toggle switch connected
    to the specified GPIO pin. The pin is pulled high in software by default
    ("off") and returns False, and connected to ground when switched "on",
    returning True.

    :param pin:       the BCM pin to which the switch is connected
    :param level:     log level
    '''
    def __init__(self, pin, level):
        self._log = Logger("toggle", level)
        self._log.info('configuring toggle on pin {}'.format(pin))
        self._pin = pin
        # The GPIO pin is set up as an input, pulled up to avoid false
        # detection. The pin is wired to connect to GND on button press.
        GPIO.setmode(GPIO.BCM)
        GPIO.setup(self._pin, GPIO.IN, pull_up_down=GPIO.PUD_UP)
        self._log.info('ready.')

    # ......................................................
    @property
    def state(self):
        '''
        Returns True when the toggle switch is turned on (connected to ground).
        '''
        _state = False if GPIO.input(self._pin) else True
        self._log.debug('state on pin {}: {}'.format(self._pin, _state))
        return _state

    # ......................................................
    def close(self):
        GPIO.cleanup() # clean up GPIO on normal exit
        self._log.info('closed.')

#EOF
