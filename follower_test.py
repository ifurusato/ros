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

from lib.i2c_scanner import I2CScanner
from lib.config_loader import ConfigLoader
from lib.enums import Orientation
from lib.logger import Logger, Level
from lib.devnull import DevNull
from lib.follower import WallFollower

_follower = None

# exception handler ............................................................
def signal_handler(signal, frame):
    print(Fore.RED + 'Ctrl-C caught: exiting...' + Style.RESET_ALL)
    if _follower:
        _follower.close()
    sys.stderr = DevNull()
    print(Fore.MAGENTA + 'exit.' + Style.RESET_ALL)
    sys.exit(0)


# main .........................................................................
def main():

    signal.signal(signal.SIGINT, signal_handler)

    print('follower test     :' + Fore.CYAN + Style.BRIGHT + ' INFO  : starting test...' + Style.RESET_ALL)
    print('follower test     :' + Fore.YELLOW + Style.BRIGHT + ' INFO  : Press Ctrl+C to exit.' + Style.RESET_ALL)

    _log = Logger("follower", Level.INFO)

    try:

        _i2c_scanner = I2CScanner(Level.WARN)
        _addresses = _i2c_scanner.getAddresses()
        hexAddresses = _i2c_scanner.getHexAddresses()
        _addrDict = dict(list(map(lambda x, y:(x,y), _addresses, hexAddresses)))
        for i in range(len(_addresses)):
            _log.debug(Fore.BLACK + Style.DIM + 'found device at address: {}'.format(hexAddresses[i]) + Style.RESET_ALL)
        vl53l1x_available = ( 0x29 in _addresses )
        ultraborg_available = ( 0x36 in _addresses )
    
        if not vl53l1x_available:
            raise OSError('VL53L1X hardware dependency not available.')
        elif not ultraborg_available:
            raise OSError('UltraBorg hardware dependency not available.')

        _log.info('starting wall follower...')

        _loader = ConfigLoader(Level.INFO)
        filename = 'config.yaml'
        _config = _loader.configure(filename)

        _follower = WallFollower(_config, Level.INFO)
        _follower.enable()

        _follower.set_position(Orientation.PORT)
        time.sleep(1.5)

        _follower.set_position(Orientation.STBD)
        time.sleep(1.5)

#       for i in range(10):
#           mm = _follower.scan()
#           time.sleep(1.0)

        

        _follower.close()
        print('follower test     :' + Fore.CYAN + Style.BRIGHT + ' INFO  : test complete.' + Style.RESET_ALL)


    except Exception:
        _log.info(traceback.format_exc())
        sys.exit(1)

if __name__== "__main__":
    main()

#EOF
