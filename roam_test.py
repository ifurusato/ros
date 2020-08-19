#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# Copyright 2020 by Murray Altheim. All rights reserved. This file is part of
# the Robot OS project and is released under the "Apache Licence, Version 2.0".
# Please see the LICENSE file included as part of this package.
#

# Import library functions we need
import sys, time, traceback
from colorama import init, Fore, Style
init()

try:
    import numpy
except ImportError:
    exit("This script requires the numpy module\nInstall with: sudo pip3 install numpy")

from lib.devnull import DevNull
from lib.enums import Direction, Speed, Velocity, SlewRate, Orientation
from lib.logger import Logger, Level
from lib.config_loader import ConfigLoader
from lib.queue import MessageQueue
from lib.arbitrator import Arbitrator
from lib.controller import Controller
from lib.motors import Motors
from lib.ifs import IntegratedFrontSensor

from lib.roam import RoamBehaviour


# ..........................................................................
def _callback_shutdown(self):
    print('callback: shutting down test...')
    sys.exit(0)


# ..............................................................................
def main():
    try:

        _loader = ConfigLoader(Level.INFO)
        filename = 'config.yaml'
        _config = _loader.configure(filename)
        _queue = MessageQueue(Level.INFO)

        _ifs = IntegratedFrontSensor(_config, _queue, Level.INFO)
        _motors = Motors(_config, None, None, Level.INFO)

        # configure Controller and Arbitrator
        _controller = Controller(_config, _ifs, _motors, _callback_shutdown, Level.INFO)
        _arbitrator = Arbitrator(_config, _queue, _controller, Level.WARN)

        print(Fore.RED   + 'roam...' + Style.RESET_ALL)
        _ifs.enable() 
        _arbitrator.start()
#       _controller.enable()
        _roam = RoamBehaviour(_motors, Level.INFO)
        _roam.roam()
        while _roam.is_roaming():
            print(Fore.BLACK + Style.DIM + '(roaming)' + Style.RESET_ALL)
            time.sleep(1.0)

        print(Fore.YELLOW + 'complete: closing...' + Style.RESET_ALL)
        _motors.close()
        print(Fore.YELLOW + 'closed.' + Style.RESET_ALL)
        sys.exit(0)

    except KeyboardInterrupt:
        print('test complete')
        sys.exit(0)
    except Exception as e:
        print(Fore.RED + Style.BRIGHT + 'error in PID controller: {}'.format(e))
        traceback.print_exc(file=sys.stdout)
        sys.exit(1)

if __name__== "__main__":
    main()

#EOF
