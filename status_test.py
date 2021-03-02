#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# Copyright 2020-2021 by Murray Altheim. All rights reserved. This file is part
# of the Robot Operating System project, released under the MIT License. Please
# see the LICENSE file included as part of this package.
#
# This tests the Status task, which turns on and off the status LED.
#

import pytest
import os, sys, signal, time, threading
from colorama import init, Fore, Style
init()

from lib.config_loader import ConfigLoader
from lib.logger import Level
from lib.status import Status

_status = None

# ..............................................................................
@pytest.mark.unit
def test_status():

    print(Fore.CYAN + "status task running...")   
    # read YAML configuration
    _loader = ConfigLoader(Level.INFO)
    filename = 'config.yaml'
    _config = _loader.configure(filename)
    
    _status = Status(_config, Level.INFO)
    _status.blink(True)
    for i in range(5):
        print(Fore.CYAN + "blinking...")   
        time.sleep(1)
    _status.blink(False)

    _status.enable()
    time.sleep(5)
    _status.close()


# call main ......................................

def main():

    try:
        test_status()
    except KeyboardInterrupt:
        print(Fore.RED + 'Ctrl-C caught: interrupted.')
    finally:
        pass

if __name__== "__main__":
    main()

