#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# Copyright 2020 by Murray Altheim. All rights reserved. This file is part of
# the Robot OS project and is released under the "Apache Licence, Version 2.0".
# Please see the LICENSE file included as part of this package.
#

import sys
import pigpio

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

class Decoder:
    '''
       Class to decode mechanical rotary encoder pulses.
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

           import time
           import pigpio

           from lib.decoder import Decoder

           pos = 0

           def callback(way):
              global pos
              pos += way
              print("pos={}".format(pos))

           decoder = Decoder(pi, 7, 8, callback)
           time.sleep(300)
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
        self.cbA = self._pi.callback(self._gpio_a, pigpio.EITHER_EDGE, self._pulse)
        self.cbB = self._pi.callback(self._gpio_b, pigpio.EITHER_EDGE, self._pulse)
        self._log.info('ready.')

    # ..........................................................................
    def _pulse(self, gpio, level, tick):
        '''
           Decode the rotary encoder pulse.

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
#       self._log.info(Fore.BLACK + 'pulse on pin: {:d}; level: {:d}'.format(gpio, level))
        if gpio == self._gpio_a:
           self._level_a = level
        else:
           self._level_b = level;
        if gpio != self._last_gpio: # debounce
           self._last_gpio = gpio
           if gpio == self._gpio_a and level == 1:
              if self._level_b == 1:
#                self._log.info('gpio B step.')
                 self.callback(1)
           elif gpio == self._gpio_b and level == 1:
              if self._level_a == 1:
#                self._log.info('gpio B step.')
                 self.callback(-1)

    # ..........................................................................
    def cancel(self):
        '''
           Cancel the rotary encoder decoder.
        '''
        self.cbA.cancel()
        self.cbB.cancel()
        # this is now done by motors.py
#       if self._pi is not None:
#           self._pi.stop()

#EOF
