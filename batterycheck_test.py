#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# Copyright 2020 by Murray Altheim. All rights reserved. This file is part of
# the Robot OS project and is released under the "Apache Licence, Version 2.0".
# Please see the LICENSE file included as part of this package.
#
# author:  Murray Altheim
# created: 2020-03-16

import time, sys, signal
from colorama import init, Fore, Style
init()

from lib.devnull import DevNull
from lib.logger import Level
from lib.config_loader import ConfigLoader
from lib.queue import MessageQueue
from lib.batterycheck import BatteryCheck

INDEFINITE = True

# exception handler ............................................................
def signal_handler(signal, frame):
    print(Fore.RED + 'Ctrl-C caught: exiting...' + Style.RESET_ALL)
    sys.stderr = DevNull()
    print(Fore.CYAN + 'exit.' + Style.RESET_ALL)
    sys.exit(0)


# ..............................................................................
def main():

    signal.signal(signal.SIGINT, signal_handler)

    try:
    
        print('batterycheck_test :' + Fore.CYAN + ' INFO  : starting test...' + Style.RESET_ALL)
    
        print('batterycheck_test :' + Fore.YELLOW + Style.BRIGHT + ' INFO  : Press Ctrl+C to exit.' + Style.RESET_ALL)
    
        # read YAML configuration
        _loader = ConfigLoader(Level.INFO)
        filename = 'config.yaml'
        _config = _loader.configure(filename)
    
        _queue = MessageQueue(Level.INFO)
        _battery_check = BatteryCheck(_config, _queue, Level.DEBUG)
        _battery_check.enable()
    
        count = 0
#       while True:
        while not _battery_check.is_ready() and count < 10:
            count += 1
            time.sleep(0.5)
    
        _battery_check.close()
        print('batterycheck_test :' + Fore.CYAN + ' INFO  : complete.' + Style.RESET_ALL)
    
    except KeyboardInterrupt:
        print('batterycheck_test :' + Fore.BLACK + Style.BRIGHT + ' INFO  : Ctrl-C caught: complete.' + Style.RESET_ALL)
        sys.exit(0)
    finally:
        sys.exit(0)

if __name__== "__main__":
    main()

#EOF
