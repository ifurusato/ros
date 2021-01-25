#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# Copyright 2020 by Murray Altheim. All rights reserved. This file is part of
# the Robot OS project and is released under the "Apache Licence, Version 2.0".
# Please see the LICENSE file included as part of this package.
#
#    This tests the Button task, which reads the state of the push button.
#

import os, sys, signal, time
from colorama import init, Fore, Style
init()

from lib.button import Button
from lib.logger import Level

# ..............................................................................
def callback_method(value):
    global activated
    activated = True
#   activated = True if False else False 
    print('button_test       :' + Fore.CYAN + ' INFO  : callback method fired; value: {:d}'.format(value) + Style.RESET_ALL)
    

# call main ....................................................................
def main():
    global activated
    activated = False

    print('button_test       :' + Fore.CYAN + ' INFO  : starting test...' + Style.RESET_ALL)

    _pin = 12
    _button = Button(_pin, callback_method, Level.INFO)

    try:
        while not activated:
            print(Fore.BLACK + 'waiting for button press on pin {:d}...'.format(_pin) + Style.RESET_ALL)
            time.sleep(1.0)
    except KeyboardInterrupt:
        print(Fore.RED + "caught Ctrl-C." + Style.RESET_ALL)
    finally:
        print("closing button...")
        _button.close()


if __name__== "__main__":
    main()

