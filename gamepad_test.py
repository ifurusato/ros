#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# Copyright 2020 by Murray Altheim. All rights reserved. This file is part of
# the Robot Operating System project and is released under the "Apache Licence,
# Version 2.0". Please see the LICENSE file included as part of this package.
#
# author:   Murray Altheim
# created:  2020-08-05
# modified: 2020-08-08
#
# This is a test class using the 8BitDo N30 Pro Gamepad, a paired Bluetooth 
# device to control the KR01.
#

import sys, time, traceback
from colorama import init, Fore, Style
init()

from lib.logger import Logger, Level
from lib.gamepad_demo import GamepadDemo

_log = Logger('gamepad-demo', Level.INFO)

try:

    _log.header('test', 'starting gamepad demo...', None)
    _gamepad_demo = GamepadDemo(Level.INFO)
    _gamepad_demo.enable()
    while _gamepad_demo.enabled:
        time.sleep(1.0)
    _gamepad_demo.close()

except KeyboardInterrupt:
    _log.info('caught Ctrl-C; exiting...')
    sys.exit(0)
except OSError:
    _log.error('unable to connect to gamepad')
    sys.exit(1)
except Exception:
    _log.error('error processing gamepad events: {}'.format(traceback.format_exc()))
    sys.exit(1)

# EOF
