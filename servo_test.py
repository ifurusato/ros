#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# Copyright 2020-2021 by Murray Altheim. All rights reserved. This file is part
# of the Robot Operating System project, released under the MIT License. Please
# see the LICENSE file included as part of this package.
#
# author:   altheim
# created:  2020-03-31
# modified: 2020-03-31
#

import time, sys, threading, traceback
from colorama import init, Fore, Style
init()

import numpy

from lib.config_loader import ConfigLoader
from lib.logger import Logger, Level
from lib.servo import Servo

# main .........................................................................
def main():

    _log = Logger("servo-test", Level.INFO)

    try:

        _log.info('starting ultrasonic scan...')

        _loader = ConfigLoader(Level.INFO)
        filename = 'config.yaml'
        _config = _loader.configure(filename)

        _number = 1
        _servo = Servo(_config, _number, Level.INFO)

#       _servo.enable()
#       _thread = threading.Thread(target=_servo.sweep, args=[])
#       _thread.start()
        for i in numpy.arange(-90.0, 90.0, 5.0):
            _servo.set_position(i)
            _log.info('position: {}'.format(i))
            time.sleep(0.5)
        _servo.set_position(0.0)
        _servo.disable()
        _thread.join()
        _log.info('servo test complete.')

    except Exception:
        _log.info(traceback.format_exc())
        sys.exit(1)

if __name__== "__main__":
    main()

#EOF
