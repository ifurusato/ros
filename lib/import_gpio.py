#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# Copyright 2020 by Murray Altheim. All rights reserved. This file is part of
# the Robot OS project and is released under the "Apache Licence, Version 2.0".
# Please see the LICENSE file included as part of this package.
#

# import GPIO
import importlib.util
from colorama import init, Fore, Style
init()

try:
    # check and import real RPi.GPIO library
    importlib.util.find_spec('RPi.GPIO')
    import RPi.GPIO as GPIO
    print('import            :' + Fore.BLACK + ' INFO  : successfully imported RPi.GPIO.' + Style.RESET_ALL)
except ImportError:
    print('import            :' + Fore.RED + ' ERROR : failed to import RPi.GPIO, using mock...' + Style.RESET_ALL)
    # If real RPi.GPIO library fails, load the fake one
    import FakeRPi.GPIO as GPIO
    print('import            :' + Fore.BLACK + ' INFO  : successfully imported FakeRPi.GPIO.' + Style.RESET_ALL)

