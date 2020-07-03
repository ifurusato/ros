#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# Copyright 2020 by Murray Altheim. All rights reserved. This file is part of
# the Robot OS project and is released under the "Apache Licence, Version 2.0".
# Please see the LICENSE file included as part of this package.
#
# author:   Murray Altheim
# created:  2020-04-27
# modified: 2020-05-21
#

# Import library functions we need
import os, sys, signal, time, traceback
from colorama import init, Fore, Style
init()

from lib.enums import Orientation
from lib.logger import Logger, Level
from lib.filewriter import FileWriter
from lib.config_loader import ConfigLoader
from lib.slewlimiter import SlewLimiter

# ..............................................................................
try:

    _log = Logger("slew test", Level.INFO)

    _loader = ConfigLoader(Level.INFO)
    filename = 'config.yaml'
    _config = _loader.configure(filename)
    _filewriter  = FileWriter(_config, 'slew', Level.INFO)
    _slewlimiter = SlewLimiter(_config, Orientation.PORT, Level.INFO)
    _slewlimiter.set_filewriter(_filewriter)

    _start_time = time.time()

#   _slewlimiter.set_rate_limit(20.0)
    _slewlimiter.enable()
    _slewlimiter.start()

    _decelerate = False

    # begin test .......................................
    _log.info('starting...')

    _current_velocity = 0.0
    _target_velocity  = 50.0
    _reached_target = 0

    while True:
        _current_velocity = _slewlimiter.slew(_current_velocity, _target_velocity)
        if _current_velocity == _target_velocity:
            if _reached_target == 0:
                _target_velocity  = 80.0
            elif _reached_target == 1:
                _target_velocity  = 30.0
            elif _reached_target >= 3 and _reached_target < 6:
                _target_velocity  = 61.0
            elif _reached_target == 7:
                _target_velocity  = 40.0
            elif _reached_target == 8:
                _target_velocity  = 20.0
            elif _reached_target >= 9 and _reached_target <= 11:
                _target_velocity  = 5.0
            elif _reached_target == 12:
                _target_velocity  = 95.0
            elif _reached_target == 13:
                _target_velocity  = 0.0
            elif _reached_target  > 13 and _reached_target < 21:
                _target_velocity  = 77.0
            elif _reached_target == 21:
                _target_velocity  = 33.0
            elif _reached_target == 22:
                _target_velocity  = 0.0
            elif _target_velocity == 0.0:
                break
            _reached_target += 1
        time.sleep(0.05)

    _slewlimiter.close_filewriter()
    _slewlimiter.reset(_target_velocity)
    _log.info('done.')

except KeyboardInterrupt:
    _log.info('slew test complete.')
except Exception as e:
    _log.error(Fore.RED + Style.BRIGHT + 'error in slew limiter: {}'.format(e))
    traceback.print_exc(file=sys.stdout)
finally:
    _log.info('finally.')

#EOF

