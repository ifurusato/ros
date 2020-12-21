#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# Copyright 2020 by Murray Altheim. All rights reserved. This file is part
# of the pimaster2ardslave project and is released under the MIT Licence;
# please see the LICENSE file included as part of this package.
#
# author:   Murray Altheim
# created:  2020-12-14
# modified: 2020-12-15
#
# A test file for use with the Pimoroni IO Expander Breakout board.
#

import time, itertools
import ioexpander as io
from colorama import init, Fore, Style
init()

print(Fore.CYAN + '''
Demonstrates handling a single analog or digital input using IO Expander.
Your sensor should be wired between ground and pin 6 for digital, pin 8 
for analog on the IO Expander. There is a flag in the file to select which 
mode.

For the digital mode a pull-up resistor will be enabled, causing your 
sensor to read 1 normally, and 0 when pressed.
''' + Style.RESET_ALL)

analog = True
ioe = io.IOE(i2c_addr=0x18)
if analog:
    pin = 8
    ioe.set_mode(pin, io.ADC)
    print(Fore.CYAN + Style.BRIGHT + 'Configured for analog mode using pin 8.' + Style.RESET_ALL)
else:
    pin = 6
    ioe.set_mode(pin, io.PIN_MODE_PU)
    print(Fore.CYAN + Style.BRIGHT + 'Configured for digital mode using pin 6.' + Style.RESET_ALL)

print(Fore.RED + '\nPress Ctrl+C to exit.\n' + Style.RESET_ALL)

last_value = 0
counter = itertools.count()
while True:
    count = next(counter)
    value = round(ioe.input(pin),2)
    if value < last_value:
        if analog:
            print(Fore.RED    + "{:d}\tbutton value: {:5.2f}v".format(count, value))
        else:
            print(Fore.RED    + "{:d}\tbutton value: {}".format(count, value))
    elif value > last_value:
        if analog:
            print(Fore.GREEN  + "{:d}\tbutton value: {:5.2f}v".format(count, value))
        else:
            print(Fore.GREEN  + "{:d}\tbutton value: {}".format(count, value))
    else:
        if analog:
            print(Fore.YELLOW + "{:d}\tbutton value: {:5.2f}v".format(count, value))
        else:
            print(Fore.YELLOW + "{:d}\tbutton value: {}".format(count, value))

    last_value = value
    time.sleep(0.5)

