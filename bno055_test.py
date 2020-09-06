#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# Copyright 2020 by Murray Altheim. All rights reserved. This file is part of
# the Robot OS project and is released under the "Apache Licence, Version 2.0".
# Please see the LICENSE file included as part of this package.
#
# author:  Murray Altheim
# created: 2020-03-16

import time, sys, signal, threading
from colorama import init, Fore, Style
init()

from lib.config_loader import ConfigLoader
from lib.devnull import DevNull
from lib.logger import Level, Logger
from lib.queue import MessageQueue
from lib.bno055_v3 import Calibration, BNO055

# exception handler ........................................................

def signal_handler(signal, frame):
    print(Fore.RED + 'Ctrl-C caught: exiting...' + Style.RESET_ALL)
#    _motors.halt()
#    Motors.cancel()
    sys.stderr = DevNull()
    print(Fore.MAGENTA + 'exit.' + Style.RESET_ALL)
    sys.exit(0)


# ..............................................................................

#_motors = Motors(None, None, Level.INFO)

def main():

    signal.signal(signal.SIGINT, signal_handler)

    _log = Logger("test", Level.INFO)

    try:

        _loader = ConfigLoader(Level.INFO)
        filename = 'config.yaml'
        _config = _loader.configure(filename)

        _queue = MessageQueue(Level.INFO)
        _bno055 = BNO055(_config, _queue, Level.INFO)

        # begin ............

        _bno055.enable()

        _tuple = _bno055.get_heading()
        _heading = _tuple[1]

#        MAX_COUNT = 25
#        # try to calibrate the BNO055
#        if _heading is None:
#            # if not calibrated, try rotating one direction
#            count = 0
#            _motors.spinPort(60.0)
#            while count < MAX_COUNT and _heading is None:
#                _heading = _bno055.get_heading()
#                count += 1
#                print(Fore.BLACK + '[{:d}] rotating counter-clockwise to calibrate...'.format(count) + Style.RESET_ALL)
#                time.sleep(0.5)
#            _motors.halt()
#            # if unsuccessful, try rotating the other direction
#            print(Fore.BLACK + 'finished rotating counter-clockwise.' + Style.RESET_ALL)
#            if _heading is None:
#                print(Fore.BLACK + 'still not calibrated: now rotating clockwise...' + Style.RESET_ALL)
#                count = 0
#                _motors.spinStarboard(80.0)
#                while count < MAX_COUNT and _heading is None:
#                    _heading = _bno055.get_heading()
#                    count += 1
#                    print(Fore.BLACK + '[{:d}] rotating clockwise to calibrate...'.format(count) + Style.RESET_ALL)
#                    time.sleep(0.5)
#                _motors.halt()
#            else:
#                print(Fore.BLACK + 'got heading value of {}.'.format(_heading) + Style.RESET_ALL)
#
#        if _heading is None:
#            print(Fore.RED + 'unable to calibrate.' + Style.RESET_ALL)
#        else:

        success = 0
        print(Fore.CYAN + 'wave robot in air until it beeps...' + Style.RESET_ALL)
        while True:
            _tuple = _bno055.get_heading()
            _calibration = _tuple[0]
            _heading     = _tuple[1]
            if _heading is None:
                _log.warning('heading:\tnone')
            elif _calibration is Calibration.NEVER:
                _log.info(Fore.CYAN + 'heading:\t{:>5.4f}° (never)'.format(_heading))
            elif _calibration is Calibration.LOST:
                _log.info(Fore.CYAN + Style.BRIGHT + 'heading:\t{:>5.4f}° (lost)'.format(_heading))
            elif _calibration is Calibration.CALIBRATED:
                success += 1
                _log.info(Fore.MAGENTA + 'heading:\t{:>5.4f}° (calibrated)'.format(_heading))
            elif _calibration is Calibration.TRUSTED:
                success += 1
                _log.info(Fore.MAGENTA + Style.BRIGHT + 'heading:\t{:>5.4f}° (trusted)'.format(_heading))
            time.sleep(0.5)
#           print(Fore.BLACK + '.' + Style.RESET_ALL)
    
    except KeyboardInterrupt:
        _bno055.close()
        _log.info('done.')
        sys.exit(0)

if __name__== "__main__":
    main()

#EOF
