#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# Copyright 2020 by Murray Altheim. All rights reserved. This file is part of
# the Robot Operating System project and is released under the "Apache Licence, 
# Version 2.0". Please see the LICENSE file included as part of this package.
#
# author:   Murray Altheim
# created:  2020-05-19
# modified: 2020-05-19
#
# see:      https://robots.org.nz/2020/05/19/four-corners/
#
# This script is used as a possible solution for the Four Corners Competition,
# as a way for a robot to locate the trajectory to a distant target.
#

import sys, traceback
from colorama import init, Fore, Style
init()

from lib.logger import Logger, Level
from lib.config_loader import ConfigLoader
#from lib.blob_v2 import Blob
from lib.blob import Blob
from lib.motors_v2 import Motors

# main .........................................................................
def main(argv):

    try:

        # read YAML configuration
        _level = Level.INFO
        _loader = ConfigLoader(_level)
        filename = 'config.yaml'
        _config = _loader.configure(filename)
        _motors = Motors(_config, None, Level.INFO)

        _ros = Blob(_config, _motors, _level)
        _ros.capture()
#       for i in range(32):
#       while True:
#           _ros.capture()

    except KeyboardInterrupt:
        print(Fore.CYAN + 'Ctrl-C interrupt.' + Style.RESET_ALL)
    except Exception:
        print(Fore.RED + Style.BRIGHT + 'error starting ros: {}'.format(traceback.format_exc()) + Style.RESET_ALL)

# call main ....................................................................

if __name__== "__main__":
    main(sys.argv[1:])

#EOF
