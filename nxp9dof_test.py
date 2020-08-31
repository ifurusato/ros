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
from lib.nxp9dof import NXP9DoF

# exception handler ........................................................
def signal_handler(signal, frame):
    print(Fore.RED + 'Ctrl-C caught: exiting...' + Style.RESET_ALL)
    sys.stderr = DevNull()
    print(Fore.MAGENTA + 'exit.' + Style.RESET_ALL)
    sys.exit(0)

# ..............................................................................

_log = Logger("nxp9dof-test", Level.INFO)
_nxp9dof = None

def main():

    signal.signal(signal.SIGINT, signal_handler)

    try:

        _loader = ConfigLoader(Level.INFO)
        filename = 'config.yaml'

        _config = _loader.configure(filename)
        _queue = MessageQueue(Level.INFO)
#       _indicator = Indicator(Level.INFO)
        _nxp9dof = NXP9DoF(_config, _queue, Level.INFO)
        _nxp9dof.enable()

        _counter = itertools.count()
        while True:
            _count = next(_counter)
#           _log.info(Fore.BLACK  + Style.NORMAL + '{:d}... '.format(_count))
            time.sleep(1.0)
    
    except KeyboardInterrupt:
        if _nxp9dof is not None:
            _nxp9dof.close()
        _log.info('done.')
        sys.exit(0)

if __name__== "__main__":
    main()

#EOF
