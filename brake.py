#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# Copyright 2020 by Murray Altheim. All rights reserved. This file is part of
# the Robot OS project and is released under the "Apache Licence, Version 2.0".
# Please see the LICENSE file included as part of this package.
#

from colorama import init, Fore, Style
init()

from lib.logger import Level, Logger
from lib.motors import Motors
from lib.config_loader import ConfigLoader

def brake():
    _log.info('braking...')
    _motors.brake()
    _motors.stop()
    _motors.close()
    _log.info('done.')

# ..............................................................................
_motors = None
_log = Logger('brake', Level.INFO)

try:

    _log.info('configuring...')
    # read YAML configuration
    _loader = ConfigLoader(Level.WARN)
    filename = 'config.yaml'
    _config = _loader.configure(filename)
    _motors = Motors(_config, None, Level.WARN)

except KeyboardInterrupt:
    _log.error('Ctrl-C caught in main: exiting...')
finally:
    _log.info('complete.')

if __name__ == '__main__':
    brake()

#EOF
