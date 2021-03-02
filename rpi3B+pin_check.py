#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# Copyright 2020-2021 by Murray Altheim. All rights reserved. This file is part
# of the Robot Operating System project, released under the MIT License. Please
# see the LICENSE file included as part of this package.
#
# author:   altheim
# created:  2020-01-18
# modified: 2020-02-06
#
# This script loops until a Ctrl-C, displaying the GPIO pins of the Raspberry Pi 3 B+
# and hilights any whose input value is high or low (depending on setting).
#
# Requires: colorama

import time, sys, itertools
import RPi.GPIO as GPIO
from colorama import init, Fore, Style
init()

# ..............................................................................
class Pin():
    def __init__(self, pin, label):
        GPIO.setup(pin, GPIO.IN, pull_up_down=GPIO.PUD_UP)
        # https://raspi.tv/2013/rpi-gpio-basics-6-using-inputs-and-outputs-together-with-rpi-gpio-pull-ups-and-pull-downs
        # pull_up_down=GPIO.PUD_DOWN. If you want/need pull-up you can change the GPIO.PUD_DOWN for GPIO.PUD_UP
        self._pin = pin
        self._label = label

    def get(self):
        '''
        Change the NORMAL and BRIGHT as desired,
        '''
        if GPIO.input(self._pin): # if low
            return Fore.GREEN + Style.NORMAL + self._label
        else:
            return Fore.GREEN + Style.BRIGHT + self._label

# ..............................................................................
def main():
    try:

        TITLE = 'Raspberry Pi 3 B+ Pinout'
        DELAY_TIME_SEC = 0.5
        GND = Fore.BLACK + Style.DIM    + 'GND   '
        CYAN_NORMAL = Fore.CYAN + Style.NORMAL
        ROWS = 35 # as tall as your screen
        NNNN = '\n' * ROWS
        INDENT = '    '

        GPIO.setmode(GPIO.BOARD)

        # column 1 ..............
        _pin07 = Pin(7, 'GPIO4')
        _pin11 = Pin(11,'GPIO17')
        _pin13 = Pin(13,'GPIO27')
        _pin15 = Pin(15,'GPIO22')
        _pin19 = Pin(19,'GPIO10')
        _pin21 = Pin(21,'GPIO9')
        _pin23 = Pin(23,'GPIO11')
        # GND 25
        # SC0 27
        _pin29 = Pin(29,'GPIO5')
        _pin31 = Pin(31,'GPIO6')
        _pin33 = Pin(33,'GPIO13')
        _pin35 = Pin(35,'GPIO19')
        _pin37 = Pin(37,'GPIO26')
        # GND 39

        # column 2 ..............
        _pin08 = Pin(8, 'GPIO14')
        _pin10 = Pin(10,'GPIO15')
        _pin12 = Pin(12,'GPIO18')
        # GND 14
        _pin16 = Pin(16,'GPIO23')
        _pin18 = Pin(18,'GPIO24')
        # GND 20
        _pin22 = Pin(22,'GPIO25')
        _pin24 = Pin(24,'GPIO8')
        _pin26 = Pin(26,'GPIO7')
        # SC1 28
        # GND 30
        _pin32 = Pin(32,'GPIO12')
        # GND 34
        _pin36 = Pin(36,'GPIO16')
        _pin38 = Pin(38,'GPIO20')
        _pin40 = Pin(40,'GPIO21')


        _counter = itertools.count()

        while True:
            print(NNNN)
            print(INDENT + Fore.WHITE + Style.BRIGHT + '\t  ' + TITLE + Style.RESET_ALL)
            print('')
            print(INDENT + Fore.RED + Style.NORMAL   + '3.3V  ' + CYAN_NORMAL + '\t(01) | (02)\t' + Fore.MAGENTA + Style.NORMAL   + '5V' + Style.RESET_ALL)
            print(INDENT + Fore.BLUE + Style.BRIGHT  + 'SDA   ' + CYAN_NORMAL + '\t(03) | (04)\t' + Fore.MAGENTA + Style.NORMAL   + '5V' + Style.RESET_ALL)
            print(INDENT + Fore.BLUE + Style.BRIGHT  + 'SCL   ' + CYAN_NORMAL + '\t(05) | (06)\t' + GND + Style.RESET_ALL)
            print(INDENT + _pin07.get()                         + CYAN_NORMAL + '\t(07) | (08)\t' + _pin08.get() + ' (TXD)' + Style.RESET_ALL)
            print(INDENT + GND                                  + CYAN_NORMAL + '\t(09) | (10)\t' + _pin10.get() + ' (RXD)' + Style.RESET_ALL)
            print(INDENT + _pin11.get()                         + CYAN_NORMAL + '\t(11) | (12)\t' + _pin12.get() + ' (PWM0)' + Style.RESET_ALL)
            print(INDENT + _pin13.get()                         + CYAN_NORMAL + '\t(13) | (14)\t' + GND + Style.RESET_ALL)
            print(INDENT + _pin15.get()                         + CYAN_NORMAL + '\t(15) | (16)\t' + _pin16.get() + Style.RESET_ALL)
            print(INDENT + Fore.RED + Style.NORMAL   + '3.3V  ' + CYAN_NORMAL + '\t(17) | (18)\t' + _pin18.get() + Style.RESET_ALL)
            print(INDENT + _pin19.get() + Fore.BLACK + '/MOSI'  + CYAN_NORMAL + '\t(19) | (20)\t' + GND + Style.RESET_ALL)
            print(INDENT + _pin21.get() + Fore.BLACK + '/MISO'  + CYAN_NORMAL + '\t(21) | (22)\t' + _pin22.get() + Style.RESET_ALL)
            print(INDENT + _pin23.get() + Fore.BLACK + '/SCLK'  + CYAN_NORMAL + '\t(23) | (24)\t' + _pin24.get() + Fore.BLACK + '/CE0' + Style.RESET_ALL)
            print(INDENT + GND                                  + CYAN_NORMAL + '\t(25) | (26)\t' + _pin26.get() + Fore.BLACK + '/CE1' + Style.RESET_ALL)
            print(INDENT + Fore.CYAN + Style.BRIGHT  + 'SC0   ' + CYAN_NORMAL + '\t(27) | (28)\t' + Fore.CYAN  + Style.BRIGHT + 'SC1' + Style.RESET_ALL)
            print(INDENT + _pin29.get()                         + CYAN_NORMAL + '\t(29) | (30)\t' + GND + Style.RESET_ALL)
            print(INDENT + _pin31.get()                         + CYAN_NORMAL + '\t(31) | (32)\t' + _pin32.get() + Style.RESET_ALL)
            print(INDENT + _pin33.get()                         + CYAN_NORMAL + '\t(33) | (34)\t' + GND + Style.RESET_ALL)
            print(INDENT + _pin35.get()                         + CYAN_NORMAL + '\t(35) | (36)\t' + _pin36.get() + Style.RESET_ALL)
            print(INDENT + _pin37.get()                         + CYAN_NORMAL + '\t(37) | (38)\t' + _pin38.get() + Style.RESET_ALL)
            print(INDENT + GND                                  + CYAN_NORMAL + '\t(39) | (40)\t' + _pin40.get() + Style.RESET_ALL)

            count = next(_counter)
            _style = Style.BRIGHT if ( count % 2 == 0 ) else Style.DIM
            print('\n\n' + Fore.BLACK + _style + INDENT + Style.NORMAL + '\tpoll {}  \tType Ctrl-C to exit.'.format(count) + Style.RESET_ALL)
            time.sleep(DELAY_TIME_SEC)

    except KeyboardInterrupt:
        print('Ctrl-C caught, exiting...')
        sys.exit(0)

if __name__== "__main__":
    main()

#EOF
