#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# Copyright 2020 by Murray Altheim. All rights reserved. This file is part of
# the Robot OS project and is released under the "Apache Licence, Version 2.0".
# Please see the LICENSE file included as part of this package.
#
# author:   altheim
# created:  2020-03-31
# modified: 2020-03-31

# Import library functions we need
import time, sys, signal, traceback
from colorama import init, Fore, Style
init()

#try:
#    import numpy
#except ImportError:
#    exit("This script requires the numpy module\nInstall with: pip3 install --user numpy")

from lib.i2c_scanner import I2CScanner
from lib.config_loader import ConfigLoader
from lib.logger import Logger, Level
from lib.devnull import DevNull
from lib.ultrasonic import UltrasonicScanner

_scanner = None

# exception handler ............................................................
def signal_handler(signal, frame):
    print(Fore.RED + 'Ctrl-C caught: exiting...' + Style.RESET_ALL)
    if _scanner:
        _scanner.close()
    sys.stderr = DevNull()
    print(Fore.MAGENTA + 'exit.' + Style.RESET_ALL)
    sys.exit(0)


# main .........................................................................
def main():

    signal.signal(signal.SIGINT, signal_handler)

    print('uscanner_test      :' + Fore.CYAN + Style.BRIGHT + ' INFO  : starting test...' + Style.RESET_ALL)
    print('uscanner_test      :' + Fore.YELLOW + Style.BRIGHT + ' INFO  : Press Ctrl+C to exit.' + Style.RESET_ALL)

    _log = Logger("uscanner", Level.INFO)
    try:
        _scanner = I2CScanner(Level.WARN)
        _addresses = _scanner.get_addresses()
        hexAddresses = _scanner.getHexAddresses()
        _addrDict = dict(list(map(lambda x, y:(x,y), _addresses, hexAddresses)))
        for i in range(len(_addresses)):
            _log.debug(Fore.BLACK + Style.DIM + 'found device at address: {}'.format(hexAddresses[i]) + Style.RESET_ALL)
        ultraborg_available = ( 0x36 in _addresses )
    
        if ultraborg_available:
            _log.info('starting ultrasonic scan...')

            _loader = ConfigLoader(Level.INFO)
            filename = 'config.yaml'
            _config = _loader.configure(filename)

            _scanner = UltrasonicScanner(_config, Level.INFO)
            _scanner.enable()
            values = _scanner.scan()
            time.sleep(1.0)
            _scanner.close()
        else:
            _log.error('required hardware dependencies not available.')

        print('uscanner_test      :' + Fore.CYAN + Style.BRIGHT + ' INFO  : test complete.' + Style.RESET_ALL)

    except Exception:
        _log.info(traceback.format_exc())
        sys.exit(1)

if __name__== "__main__":
    main()

#EOF
