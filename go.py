#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# Copyright 2020 by Murray Altheim. All rights reserved. This file is part of
# the Robot OS project and is released under the "Apache Licence, Version 2.0".
# Please see the LICENSE file included as part of this package.
#
# author:   Murray Altheim
# created:  2020-02-22
#

import signal, traceback
from colorama import init, Fore, Style
init()

from ros import ROS

from lib.logger import Level
from feature_importer import FeatureImporter

# ==============================================================================

# exception handler ............................................................

def signal_handler(signal, frame):
    print(Fore.MAGENTA + 'Ctrl-C caught: exiting...' + Style.RESET_ALL)
    _ros.close()
    print(Fore.MAGENTA + 'exit.' + Style.RESET_ALL)

# main .........................................................................

_wait_for_button_press = True
_ros = ROS(_wait_for_button_press)
_feature_importer = FeatureImporter(_ros, Level.INFO)

def main():

    signal.signal(signal.SIGINT, signal_handler)

    try:

        _feature_importer.scan()

        _ros.configure()

        _ros.start()

    except Exception:
        print(Fore.RED + Style.BRIGHT + 'error starting ros: {}'.format(traceback.format_exc()) + Style.RESET_ALL)
        _ros.close()

# call main ....................................................................
if __name__== "__main__":
    main()

# prevent Python script from exiting abruptly
#signal.pause()

#EOF
