#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# Copyright 2021 by Murray Altheim. All rights reserved. This file is part of
# the Robot OS project and is released under the "Apache Licence, Version 2.0".
# Please see the LICENSE file included as part of this package.
#
# author:   Murray Altheim
# created:  2021-02-25
# modified: 2021-02-25
#

import pytest
import time, traceback
from colorama import init, Fore, Style
init()

from lib.fan import Fan
from lib.logger import Level
from lib.config_loader import ConfigLoader

# ..............................................................................
@pytest.mark.unit
def test_fan():
    _fan = None
    try:
        # read YAML configuration
        _loader = ConfigLoader(Level.INFO)
        filename = 'config.yaml'
        _config = _loader.configure(filename)
        _fan = Fan(_config, Level.INFO)

        while True:
            print("Switching fan on!")
            _fan.enable()
            time.sleep(5)
            print("Switching fan off!")
            _fan.disable()
            time.sleep(5)

    except KeyboardInterrupt:
        print("Disabling switch")
        if _fan:
            _fan.disable()

# ..............................................................................
def main():
    try:
        test_fan()
    except KeyboardInterrupt:
        print(Fore.RED + 'Ctrl-C caught: complete.')
    except Exception as e:
        print(Fore.RED + 'error closing: {}\n{}'.format(e, traceback.format_exc()))

if __name__== "__main__":
    main()

#EOF
