#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# Copyright 2020-2021 by Murray Altheim. All rights reserved. This file is part
# of the Robot Operating System project, released under the MIT License. Please
# see the LICENSE file included as part of this package.
#
# created:  2020-05-17
# modified: 2021-01-29
#

import sys

from lib.config_loader import ConfigLoader
from lib.logger import Level, Logger
from lib.clock import Clock
from lib.message_bus import MessageBus
from lib.message_factory import MessageFactory
from lib.motor_configurer import MotorConfigurer
from lib.motors import Motors

_motors = None

# main .........................................................................
def main(argv):

    try:
        _log = Logger('brake', Level.INFO)
        _log.info('configuring...')
        # read YAML configuration
        _loader = ConfigLoader(Level.WARN)
        _config = _loader.configure()

        _log.info('creating message factory...')
        _message_factory = MessageFactory(Level.INFO)
        _log.info('creating message bus...')
        _message_bus = MessageBus(Level.INFO)
        _log.info('creating clock...')
        _clock = Clock(_config, _message_bus, _message_factory, Level.WARN)

        _motor_configurer = MotorConfigurer(_config, _clock, Level.INFO)
        _motors = _motor_configurer.get_motors()

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
