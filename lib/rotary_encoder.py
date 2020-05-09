#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# Copyright 2020 by Murray Altheim. All rights reserved. This file is part of
# the Robot OS project and is released under the "Apache Licence, Version 2.0".
# Please see the LICENSE file included as part of this package.
#

import sys

from colorama import init, Fore, Style
init()

try:
    import pigpio
    pi = pigpio.pi()
    print('import            :' + Fore.BLACK + ' INFO  : successfully imported pigpio.' + Style.RESET_ALL)
except ImportError:
    print('import            :' + Fore.RED + ' ERROR : failed to import pigpio, using mock...' + Style.RESET_ALL)
    from mock_pi import MockPi as Pi
    pi = MockPi()
#   sys.exit(1)

class Decoder:

   """Class to decode mechanical rotary encoder pulses."""

   def __init__(self, pi, gpioA, gpioB, callback):

      """
      Instantiate the class with the pi and gpios connected to
      rotary encoder contacts A and B.  The common contact
      should be connected to ground.  The callback is
      called when the rotary encoder is turned.  It takes
      one parameter which is +1 for clockwise and -1 for
      counterclockwise.

      EXAMPLE

      import time
      import pigpio

      import rotary_encoder

      pos = 0

      def callback(way):
         global pos
         pos += way
         print("pos={}".format(pos))

      decoder = rotary_encoder.Decoder(pi, 7, 8, callback)
      time.sleep(300)
      decoder.cancel()

      """

      self._pi = pi
#     print( 'pi: {}'.format(self._pi))
      self.gpioA = gpioA
      self.gpioB = gpioB
      self.callback = callback

      self.levA = 0
      self.levB = 0
      self.lastGpio = None
      self._pi.set_mode(gpioA, pigpio.INPUT)
      self._pi.set_mode(gpioB, pigpio.INPUT)
      self._pi.set_pull_up_down(gpioA, pigpio.PUD_UP)
      self._pi.set_pull_up_down(gpioB, pigpio.PUD_UP)
      self.cbA = self._pi.callback(gpioA, pigpio.EITHER_EDGE, self._pulse)
      self.cbB = self._pi.callback(gpioB, pigpio.EITHER_EDGE, self._pulse)


   def _pulse(self, gpio, level, tick):

      """
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
      """

      if gpio == self.gpioA:
         self.levA = level
      else:
         self.levB = level;

      if gpio != self.lastGpio: # debounce
         self.lastGpio = gpio

         if   gpio == self.gpioA and level == 1:
            if self.levB == 1:
               self.callback(1)
         elif gpio == self.gpioB and level == 1:
            if self.levA == 1:
               self.callback(-1)

   def cancel(self):
      """
      Cancel the rotary encoder decoder.
      """
      self.cbA.cancel()
      self.cbB.cancel()
      if self._pi is not None:
          self._pi.stop()


#ROTARY_ENCODER_A1 = 27
#ROTARY_ENCODER_B1 = 22
#ROTARY_ENCODER_A2 = 18
#ROTARY_ENCODER_B2 = 23
#
#ROTARY_ENCODER_A = ROTARY_ENCODER_A2
#ROTARY_ENCODER_B = ROTARY_ENCODER_B2
#
#if __name__ == "__main__":
#
#    print("-- main() ......................................................... ")
#
#    import time
#    import rotary_encoder
#
#    pos = 0
#
#    def callback(way):
#        global pos
#        pos += way
#        print("pos={}".format(pos))
#
#    try:
#
#        import pigpio
#        _pi = pigpio.pi()
#
#        decoder = rotary_encoder.Decoder(_pi, ROTARY_ENCODER_A, ROTARY_ENCODER_B, callback)
#
#        while True:
#            print('.')
#            time.sleep(1.0)
# 
#    except ImportError:
#        print(Fore.RED + "This script requires pigpio. Exiting..." + Style.RESET_ALL)
#        sys.exit(1)
#
#    except KeyboardInterrupt:
#        print(Fore.RED + 'interrupted.' + Style.RESET_ALL)
#        if decoder is not None:
#            decoder.cancel()

#EOF
