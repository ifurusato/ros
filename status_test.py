#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# Copyright 2020 by Murray Altheim. All rights reserved. This file is part of
# the Robot OS project and is released under the "Apache Licence, Version 2.0".
# Please see the LICENSE file included as part of this package.
#
#    This tests the Status task, which turns on and off the status LED.
#

import os, sys, signal, time, threading
import RPi.GPIO as GPIO

from lib.logger import Logger, Level
from lib.config_loader import ConfigLoader
from lib.status import Status

# call main ......................................

def main():

    _log = Logger("status test", Level.INFO)

    _log.info("status task run()")   

    # read YAML configuration
    _loader = ConfigLoader(Level.INFO)
    filename = 'config.yaml'
    _config = _loader.configure(filename)
    
    _status = Status(_config, GPIO, Level.INFO)

    try: 
        _status.blink(True)
        for i in range(10):
            _log.info("blinking...")   
            time.sleep(1)
        _status.blink(False)

        _status.enable()
        time.sleep(5)

    except KeyboardInterrupt:
        _log.info('Ctrl-C caught: interrupted.')
    finally:
        _log.info("status task close()")   
        _status.close()

if __name__== "__main__":
    main()

