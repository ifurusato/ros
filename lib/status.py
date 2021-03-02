#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# Copyright 2020-2021 by Murray Altheim. All rights reserved. This file is part
# of the Robot Operating System project, released under the MIT License. Please
# see the LICENSE file included as part of this package.
#
# author:   Murray Altheim
# created:  2020-01-17
# modified: 2020-01-17
#

import time, threading
import RPi.GPIO as GPIO
#from .import_gpio import *
#import lib.import_gpio
from lib.logger import Level, Logger

# ..............................................................................
class Status():
    '''
    Status Task: turns the status light on and off when it is set enabled or disabled.

    This also provides a thread-based blinker using blink(), halted by disable().

    Note that its status light functionality is not affected by enable or disable,
    as the purpose of this behaviour is to show that the overall OS is running.
    '''

    # ..........................................................................
    def __init__(self, config, level):
        self._log = Logger('status', level)
        self._log.debug('initialising...')
        if config is None:
            raise ValueError('no configuration provided.')
        _config = config['ros'].get('status')
        self._led_pin = _config.get('led_pin')
        self._gpio = GPIO
        self._gpio.setwarnings(False)
        self._gpio.setmode(GPIO.BCM)
        self._gpio.setup(self._led_pin, GPIO.OUT, initial=GPIO.LOW)
        self._blink_thread = None
        self._blinking = False
        self._log.info('ready.')


    # ..........................................................................
    def __blink__(self):
        '''
        The blinking thread.
        '''
        while self._blinking:
            self._gpio.output(self._led_pin,True)
            time.sleep(0.5)
            self._gpio.output(self._led_pin,False)
            time.sleep(0.5)
        self._log.info('blink complete.')


    # ..........................................................................
    def blink(self, active):
        if active:
            if self._blink_thread is None:
                self._log.debug('starting blink...')
                self._blinking = True
                self._blink_thread = threading.Thread(target=Status.__blink__, args=[self,])
                self._blink_thread.start()
            else:
                self._log.warning('ignored: blink already started.')
        else:
            if self._blink_thread is None:
                self._log.debug('ignored: blink thread does not exist.')
            else:
                self._log.info('stop blinking...')
                self._blinking = False
                self._blink_thread.join()
                self._blink_thread = None
                self._log.info('blink thread ended.')


    # ..........................................................................
    def enable(self):
        self._log.info('enable status light.')
        self._gpio.output(self._led_pin, True)


    # ..........................................................................
    def disable(self):
        self._log.info('disable status light.')
        self._gpio.output(self._led_pin,False)
        self._blinking = False


    # ..........................................................................
    def close(self):
        self._log.info('closing status light...')
        self._blinking = False
        self._gpio.output(self._led_pin,False)
        self._log.info('status light closed.')


#EOF
