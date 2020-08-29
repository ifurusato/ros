#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# Copyright 2020 by Murray Altheim. All rights reserved. This file is part of
# the Robot OS project and is released under the "Apache Licence, Version 2.0".
# Please see the LICENSE file included as part of this package.
#
# author:   Murray Altheim
# created:  2020-08-15
# modified: 2020-08-28
#
#  Tests the Compass class, which uses a BNO055 for a heading reading.
#

import time, sys, signal, itertools
from colorama import init, Fore, Style
init()

from lib.config_loader import ConfigLoader
from lib.devnull import DevNull
from lib.logger import Level, Logger
from lib.queue import MessageQueue
from lib.indicator import Indicator
from lib.compass import Compass

# exception handler ........................................................
def signal_handler(signal, frame):
    print(Fore.RED + 'Ctrl-C caught: exiting...' + Style.RESET_ALL)
    sys.stderr = DevNull()
    print(Fore.MAGENTA + 'exit.' + Style.RESET_ALL)
    sys.exit(0)

# ..............................................................................

_log = Logger("compass-test", Level.INFO)
_compass = None

def main():

    signal.signal(signal.SIGINT, signal_handler)

    try:

        _loader = ConfigLoader(Level.INFO)
        filename = 'config.yaml'

        _config = _loader.configure(filename)
        _queue = MessageQueue(Level.INFO)
        _indicator = Indicator(Level.INFO)
        _compass = Compass(_config, _queue, _indicator, Level.INFO)
        _compass.enable()

        _counter = itertools.count()
        print(Fore.CYAN + 'wave robot in air until it beeps...' + Style.RESET_ALL)
        while True:
            _count = next(_counter)
            _log.info(Fore.BLACK  + Style.NORMAL + '{:d}... '.format(_count))
            time.sleep(1.0)
    
    except KeyboardInterrupt:
        if _compass is not None:
            _compass.close()
        _log.info('done.')
        sys.exit(0)

if __name__== "__main__":
    main()

#EOF
