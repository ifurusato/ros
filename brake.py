#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# Copyright 2020 by Murray Altheim. All rights reserved. This file is part of
# the Robot OS project and is released under the "Apache Licence, Version 2.0".
# Please see the LICENSE file included as part of this package.
#
# created:  2020-05-17
# modified: 2021-01-29
#

import sys

from lib.logger import Level, Logger
from lib.motors import Motors
from lib.config_loader import ConfigLoader

_motors = None

# main .........................................................................
def main(argv):

    try:
        _log = Logger('brake', Level.INFO)
        _log.info('configuring...')
        # read YAML configuration
        _loader = ConfigLoader(Level.WARN)
        _config = _loader.configure()
        _motors = Motors(_config, None, Level.INFO)
        _log.info('braking...')
        _motors.brake()
        _log.info('done.')
    except KeyboardInterrupt:
        _log.error('Ctrl-C caught in main: exiting...')
    finally:
        if _motors:
            _motors.stop()
            _motors.close()
        _log.info('complete.')

if __name__ == '__main__':
    main(sys.argv[1:])

#EOF
