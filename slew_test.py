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

from lib.logger import Logger, Level
from lib.config_loader import ConfigLoader
from lib.slew import SlewLimiter
from lib.rate import Rate

# ..............................................................................
try:

    _log = Logger("slew test", Level.INFO)

    _loader = ConfigLoader(Level.INFO)
    filename = 'config.yaml'
    _config = _loader.configure(filename)

    _limiter = SlewLimiter(_config, None, Level.INFO)
#   _limiter.set_rate_limit(SlewRate.NORMAL)
    _limiter.enable()

    _decelerate = True

    # begin test .......................................
    _log.info('starting...')

    _rate = Rate(20) # Hz
    _motor_velocity  = 0.0
    _target_velocity = 80.0

    while _motor_velocity < _target_velocity:
        _motor_velocity = _limiter.slew(_motor_velocity, _target_velocity)
        _log.info(Fore.CYAN + Style.BRIGHT + 'velocity: {:>5.2f} -> {:>5.2f}.'.format(_motor_velocity, _target_velocity))
        _rate.wait()

    if _decelerate:
        _target_velocity = 0.0
        while _motor_velocity > _target_velocity:
            _motor_velocity = _limiter.slew(_motor_velocity, _target_velocity)
            _log.info(Fore.YELLOW + Style.NORMAL + 'velocity: {:>5.2f} -> {:>5.2f}.'.format(_motor_velocity, _target_velocity))
            _rate.wait()


    _log.info('done.')

except KeyboardInterrupt:
    _log.info('slew test complete.')
except Exception as e:
    _log.error(Fore.RED + Style.BRIGHT + 'error in slew limiter: {}'.format(e))
    traceback.print_exc(file=sys.stdout)
finally:
    _log.info('finally.')

#EOF

