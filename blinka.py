#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# Copyright 2020 by Murray Altheim. All rights reserved. This file is part of
# the Robot OS project and is released under the "Apache Licence, Version 2.0".
# Please see the LICENSE file included as part of this package.
#
# author:   Murray Altheim
# created:  2020-01-17
# modified: 2020-01-17
#
#  Blinka: counts in BCD across three GPIO pins. This is used for testing
#  components that react to pin changes, such as Itsy Bitsy M4 Express in
#  an I²C slave configuration.
#

import sys, signal, time, traceback, threading
import lib.import_gpio
import RPi.GPIO as GPIO
#from lib.import_gpio import *
from colorama import init, Fore, Style
init()

from lib.devnull import DevNull
from lib.logger import Level, Logger

# ..............................................................................
class Blinka():
    def __init__(self, GPIO, level):
        self._log = Logger('blinka', level)
        self._log.debug('initialising...')
        self._pin_0 = 5
        self._pin_1 = 6
        self._pin_2 = 13
        self.GPIO = GPIO
        self.GPIO.setwarnings(False)
        self.GPIO.setmode(GPIO.BCM)
        self.GPIO.setup(self._pin_0, GPIO.OUT, initial=GPIO.LOW)
        self.GPIO.setup(self._pin_1, GPIO.OUT, initial=GPIO.LOW)
        self.GPIO.setup(self._pin_2, GPIO.OUT, initial=GPIO.LOW)
        self._blink_thread = None
        self._enabled  = False
        self._delay_sec = 0.3
        self._log.info('ready.')

    # ..........................................................................
    def __blink__(self):
        '''
            The blinking thread.
        '''
        while self._enabled:
            for i in range(0, 8):
                _s = '{:03b}'.format(i)
                _b0 = (_s[2] == '1')
                _b1 = (_s[1] == '1')
                _b2 = (_s[0] == '1')
                self._log.info(Fore.GREEN + Style.BRIGHT + '{}: '.format(_s) + Fore.CYAN + '\t{}\t{}\t{}'.format(_b2, _b1, _b0))
                self.GPIO.output(self._pin_0,_b0)
                self.GPIO.output(self._pin_1,_b1)
                self.GPIO.output(self._pin_2,_b2)
                time.sleep(self._delay_sec)
#               self.GPIO.output(self._pin_0,False)
#               self.GPIO.output(self._pin_1,False)
#               self.GPIO.output(self._pin_2,False)
#               time.sleep(0.2)
            self._log.info('and again...')
        self._log.info('blink complete.')

    # ..........................................................................
    def blink(self, active):
        if active:
            if self._blink_thread is None:
                self._log.debug('starting blink...')
                self._enabled = True
                self._blink_thread = threading.Thread(target=Blinka.__blink__, args=[self,])
                self._blink_thread.start()
            else:
                self._log.warning('ignored: blink already started.')
        else:
            if self._blink_thread is None:
                self._log.debug('ignored: blink thread does not exist.')
            else:
                self._log.info('stop blinking...')
                self._enabled = False
                self._blink_thread.join()
                self._blink_thread = None
                self._log.info('blink thread ended.')

    # ..........................................................................
    def on(self):
        self.GPIO.output(self._pin_0, True)
        self.GPIO.output(self._pin_1, True)
        self.GPIO.output(self._pin_2, True)

    # ..........................................................................
    def off(self):
        self.GPIO.output(self._pin_0, False)
        self.GPIO.output(self._pin_1, False)
        self.GPIO.output(self._pin_2, False)

    # ..........................................................................
    def enable(self):
        self._log.info('enable blinka.')
        self.on()

    # ..........................................................................
    def disable(self):
        self._log.info('disable blinka.')
        self.off()
        self._enabled = False


_blinka = Blinka(GPIO, Level.INFO)

# exception handler ........................................................
def signal_handler(signal, frame):
    print(Fore.YELLOW + 'signal handler caught Ctrl-C; exiting...')
    if _blinka:
        _blinka.disable()
    sys.stderr = DevNull()
    print('exit.')
    sys.exit(0)


# main .........................................................................
def main(argv):

    signal.signal(signal.SIGINT, signal_handler)

    try:

        _blinka.blink(True)
        while True:
#       for i in range(3):
            time.sleep(8.0)
#       _blinka.off()
        _blinka.disable()

    except KeyboardInterrupt:
        print(Fore.CYAN + Style.BRIGHT + 'caught Ctrl-C; exiting...')
        _blinka.disable()
    except Exception:
        print(Fore.RED + Style.BRIGHT + 'error starting ros: {}'.format(traceback.format_exc()) + Style.RESET_ALL)
        _blinka.disable()
    finally:
        print(Fore.CYAN + Style.NORMAL + 'finally.')
        _blinka.disable()

# call main ....................................................................
if __name__== "__main__":
    main(sys.argv[1:])


#EOF
