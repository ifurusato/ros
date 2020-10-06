#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# Copyright 2020 by Murray Altheim. All rights reserved. This file is part of
# the Robot OS project and is released under the "Apache Licence, Version 2.0".
# Please see the LICENSE file included as part of this package.
#
# author:   Murray Altheim
# created:  2020-09-27
# modified: 2020-09-27
#
#

import sys, os
from colorama import init, Fore, Style
init()

from lib.logger import Logger, Level
from lib.config_loader import ConfigLoader
from lib.gamepad import GamepadScan

# main .........................................................................
def main(argv):

    _loader = ConfigLoader(Level.WARN)
    filename = 'config.yaml'
    _config = _loader.configure(filename)
    _gp_scan = GamepadScan(_config, Level.INFO)
    _matches = _gp_scan.check_gamepad_device()
    print(Fore.CYAN + 'done: {}'.format(_matches) + Style.RESET_ALL)

# call main ....................................................................
if __name__== "__main__":
    main(sys.argv[1:])

#EOF
