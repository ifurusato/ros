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

import sys, time, traceback, threading
from colorama import init, Fore, Style
init()

from lib.logger import Logger, Level
from lib.gamepad_demo import GamepadDemo

_log = Logger('gamepad-test', Level.INFO)
_motors = None
_gamepad_demo = None
_exit_code = 0

try:

    _main_thread = threading.main_thread()
    _main_thread.name = 'main'

    _log.header('test', 'starting gamepad demo...', None)
    _gamepad_demo = GamepadDemo(Level.INFO)
    _gamepad_demo.enable()
    _motors = _gamepad_demo.get_motors()
    while _gamepad_demo.enabled:
        time.sleep(1.0)
    _log.info('exited loop.')
    time.sleep(1.0)

except KeyboardInterrupt:
    _log.info('caught Ctrl-C; exiting...')
except OSError:
    _exit_code = 1
    _log.error('unable to connect to gamepad')
except Exception:
    _exit_code = 1
    _log.error('error processing gamepad events: {}'.format(traceback.format_exc()))
finally:
    _log.info('closing...')
    if _motors is not None:
        if _motors.is_in_motion():
            _log.info(Fore.YELLOW + 'stopping motors...')
            _motors.brake()
        _motors.close()
    time.sleep(1.0)
    if _gamepad_demo is not None:
        _gamepad_demo.close()
#   _log.info(Fore.YELLOW + 'still-open threads:')
#   for thread in threading.enumerate(): 
#       _log.info(Fore.YELLOW + 'thread {} is alive? {}'.format(thread.name, thread.is_alive()))
    time.sleep(1.0)
    _log.info('complete.')

# EOF
