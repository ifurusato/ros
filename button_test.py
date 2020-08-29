#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# Copyright 2020 by Murray Altheim. All rights reserved. This file is part of
# the Robot OS project and is released under the "Apache Licence, Version 2.0".
# Please see the LICENSE file included as part of this package.
#
#    This tests the Button task, which reads the state of the push button.
#

import os, sys, signal, time, threading
from colorama import init, Fore, Style
init()

from lib.button import Button
from lib.config_loader import ConfigLoader
from lib.queue import MessageQueue
from lib.logger import Level

# call main ....................................................................
def main():

    print('button_test       :' + Fore.CYAN + ' INFO  : starting test...' + Style.RESET_ALL)

    print('button_test       :' + Fore.BLUE + Style.BRIGHT + ' INFO  : to pass test, press button for both ON and OFF states...' + Style.RESET_ALL)

    # read YAML configuration
    _loader = ConfigLoader(Level.INFO)
    filename = 'config.yaml'
    _config = _loader.configure(filename)
    
    _queue = MessageQueue(Level.INFO)
    _button = Button(_config, _queue, threading.Lock())
    _button.start()

    while not _button.get():
        print('button_test       : ' + Fore.RED + Style.BRIGHT + "button OFF" + Fore.CYAN + Style.NORMAL + ' (press button to turn ON)' + Style.RESET_ALL)   
        time.sleep(1)
    while _button.get():
        print('button_test       : ' + Fore.GREEN + Style.BRIGHT + "button ON" + Fore.CYAN + Style.NORMAL + ' (press button to turn OFF)' + Style.RESET_ALL)
        time.sleep(1)
    while not _button.get():
        print('button_test       : ' + Fore.RED + Style.BRIGHT + "button OFF" + Fore.CYAN + Style.NORMAL + ' (press button to turn ON)' + Style.RESET_ALL)   
        time.sleep(1)

    print("button task close()")   
    _button.close()


if __name__== "__main__":
    main()

