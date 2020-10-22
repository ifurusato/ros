#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# Copyright 2020 by Murray Altheim. All rights reserved. This file is part of
# the Robot OS project and is released under the "Apache Licence, Version 2.0".
# Please see the LICENSE file included as part of this package.
#
# author:  Murray Altheim
# created: 2020-03-16

import time, sys, signal
from colorama import init, Fore, Style
init()

from lib.devnull import DevNull
from lib.logger import Logger, Level
from lib.config_loader import ConfigLoader
from lib.queue import MessageQueue
from lib.batterycheck import BatteryCheck

INDEFINITE = True

# exception handler ............................................................
def signal_handler(signal, frame):
    print(Fore.RED + 'Ctrl-C caught: exiting...' + Style.RESET_ALL)
    sys.stderr = DevNull()
    print(Fore.CYAN + 'exit.' + Style.RESET_ALL)
    sys.exit(0)


# ..............................................................................
def main():

    signal.signal(signal.SIGINT, signal_handler)

    try:

        _log = Logger("batcheck test", Level.INFO)
        _log.header('battery check', 'Starting test...', '[1/3]')
        _log.info(Fore.RED + 'Press Ctrl+C to exit.')

        # read YAML configuration
        _loader = ConfigLoader(Level.INFO)
        filename = 'config.yaml'
        _config = _loader.configure(filename)

        _log.header('battery check', 'Creating objects...', '[2/3]')
        _queue = MessageQueue(Level.INFO)
        _message_factory = MessageFactory(Level.INFO)
        _battery_check = BatteryCheck(_config, _queue, _message_factory, Level.INFO)
        _battery_check.enable()
        _battery_check.set_enable_messaging(True)
        _log.header('battery check', 'Enabling battery check...', '[3/3]')

        _log.info('ready? {}'.format(_battery_check.is_ready()))

        count = 0
        while not _battery_check.is_ready() and count < 10:
            count += 1
            time.sleep(0.5)

        while _battery_check.get_count() < 30:
            time.sleep(0.5)

        _battery_check.close()
        _log.info('complete.')

    except KeyboardInterrupt:
        _log.info('Ctrl-C caught: complete.')
    except Exception as e:
        _log.error('error closing: {}\n{}'.format(e, traceback.format_exc()))
    finally:
        sys.exit(0)

if __name__== "__main__":
    main()

#EOF
