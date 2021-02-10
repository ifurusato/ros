#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# Copyright 2020 by Murray Altheim. All rights reserved. This file is part of
# the Robot OS project and is released under the "Apache Licence, Version 2.0".
# Please see the LICENSE file included as part of this package.
#

import sys, traceback
import pigpio
import RPi.GPIO as GPIO

from colorama import init, Fore, Style
init()

from lib.logger import Level, Logger

#try:
#    import pigpio
#    pi = pigpio.pi()
#    print('import            :' + Fore.BLACK + ' INFO  : successfully imported pigpio.' + Style.RESET_ALL)
#except ImportError:
#    print('import            :' + Fore.RED + ' ERROR : failed to import pigpio, using mock...' + Style.RESET_ALL)
#    from mock_pi import MockPi as Pi
#    pi = MockPi()
#    sys.exit(1)

class Decoder(object):
    '''
    Class to decode mechanical rotary encoder pulses.

    Originally written with pigpio's pi.callback() method, now 
    re-implemented using interrupts from the RPi.GPIO library.

    Decodes the rotary encoder A and B pulses, e.g.:

                     +---------+         +---------+      0
                     |         |         |         |
           A         |         |         |         |
                     |         |         |         |
           +---------+         +---------+         +----- 1

               +---------+         +---------+            0
               |         |         |         |
           B   |         |         |         |
               |         |         |         |
           ----+         +---------+         +---------+  1

    '''

    # ..........................................................................
    def __init__(self, pi, orientation, gpio_a, gpio_b, callback, level):
        '''
        Instantiate the class with the pi and gpios connected to
        rotary encoder contacts A and B. The common contact should
        be connected to ground. The callback is called when the
        rotary encoder is turned. It takes one parameter which is
        +1 for clockwise and -1 for counterclockwise.

        EXAMPLE

        from lib.decoder import Decoder

        pos = 0

        def callback(self, gpio, level, tick):
           global pos
           pos += way
           print("pos={}".format(pos))

        pin_a = 17
        pin_b = 18
        decoder = Decoder(pi, pin_a, pin_b, callback)
        ...
        decoder.cancel()

        :param pi:           the Pigpio connection to the Raspberry Pi
        :param orientation:  the motor orientation
        :param gpio_a:        pin number for A
        :param gpio_b:        pin number for B
        :param callback:     the callback method
        :param level:        the log Level
        '''
        self._log = Logger('enc:{}'.format(orientation.label), level)
        self._pi = pi
        self._gpio_a = gpio_a
        self._gpio_b = gpio_b
        self._log.info('pin A: {:d}; pin B: {:d}'.format(self._gpio_a,self._gpio_b))
        self.callback = callback
        self._level_a = 0
        self._level_b = 0
        self._last_gpio = None

        self._pi.set_mode(self._gpio_a, pigpio.INPUT)
        self._pi.set_mode(self._gpio_b, pigpio.INPUT)
        self._pi.set_pull_up_down(self._gpio_a, pigpio.PUD_UP)
        self._pi.set_pull_up_down(self._gpio_b, pigpio.PUD_UP)
#       _edge = pigpio.RISING_EDGE   # default
#       _edge = pigpio.FALLING_EDGE
        _edge = pigpio.EITHER_EDGE
        self.cbA = self._pi.callback(self._gpio_a, _edge, self._pulse_a)
        self.cbB = self._pi.callback(self._gpio_b, _edge, self._pulse_b)

#       the following (untested) implementation uses GPIO interrupts:
#       _success = False
#       try:
#           GPIO.setmode(GPIO.BCM)
#           GPIO.setup(self._gpio_a, GPIO.IN, pull_up_down=GPIO.PUD_UP)
#           GPIO.setup(self._gpio_b, GPIO.IN, pull_up_down=GPIO.PUD_UP)
#           # RISING, FALLING or BOTH?
#           GPIO.add_event_detect(self._gpio_a, GPIO.RISING, callback=self._pulse_a, bouncetime=100)
#           GPIO.add_event_detect(self._gpio_b, GPIO.RISING, callback=self._pulse_b, bouncetime=100)
#           _success = True
#       except Exception as e:
#           self._log.error('error configuring interrupts: {}\n{}'.format( e, traceback.format_exc()))
#       finally:
#           if _success:
#               self._log.info('ready.')
#           else:
#               self._log.warning('failed to configure GPIO interrupts for motor encoders.')
#           sys.exit(0 if _success else 1)

    # ..........................................................................
    def _pulse_a(self, gpio, level, tick):
#       self._log.info('_pulse_A level: {}; tick: {}'.format(level, tick))
        self._level_a = level
        if level == 1 and self._level_b == 1:
            self.callback(1)

    # ..........................................................................
    def _pulse_b(self, gpio, level, tick):
#       self._log.info('_pulse_B level: {}; tick: {}'.format(level, tick))
        self._level_b = level;
        if level == 1 and self._level_a == 1:
            self.callback(-1)

    # ..........................................................................
    def _pulse(self, gpio, level, tick):
        if gpio == self._gpio_a:
           self._level_a = level
        else:
           self._level_b = level;
        if gpio != self._last_gpio: # debounce
           self._last_gpio = gpio
           if gpio == self._gpio_a and level == 1:
              if self._level_b == 1:
                 self.callback(1)
           elif gpio == self._gpio_b and level == 1:
              if self._level_a == 1:
                 self.callback(-1)

    # ..........................................................................
    def cancel(self):
        '''
        Cancel the rotary encoder decoder.
        '''
        self.cbA.cancel()
        self.cbB.cancel()

#EOF
