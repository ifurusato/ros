#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# Copyright 2020-2021 by Murray Altheim. All rights reserved. This file is part
# of the Robot Operating System project, released under the MIT License. Please
# see the LICENSE file included as part of this package.
#
# author:   Murray Altheim
# created:  2021-01-24
# modified: 2021-01-24
#

import RPi.GPIO as GPIO
from colorama import init, Fore, Style
init()

from lib.logger import Level, Logger

# ..............................................................................
class Button(object):
    '''
    Executes a callback upon pressing a button connected to the specified
    GPIO pin. The button should be pulled high and connected to ground
    when pressed.

    :param pin:       the BCM pin to which the button is connected
    :param callback:  the callback to execute upon button activation
    :param level:     log level
    '''
    def __init__(self, pin, callback, level):
        self._log = Logger("button", level)
        _callback = callback
        self._log.info('configuring button for callback on pin {}'.format(pin))
        GPIO.setmode(GPIO.BCM)
        # The GPIO pin is set up as an input, pulled up to avoid false
        # detection. The pin is wired to connect to GND on button press,
        # it is configured to detect a falling edge.
        GPIO.setup(pin, GPIO.IN, pull_up_down=GPIO.PUD_UP)

        # when a falling edge is detected on the pin, regardless of whatever
        # else is happening in the program, the function _callback will be run
        # 'bouncetime=300' includes the bounce control written into interrupts2a.py
        GPIO.add_event_detect(pin, GPIO.FALLING, callback=_callback, bouncetime=300)
        self._log.info('ready.')

    # ......................................................
    def close(self):
        GPIO.cleanup() # clean up GPIO on normal exit
        self._log.info('closed.')

