#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# Copyright 2020-2021 by Murray Altheim. All rights reserved. This file is part
# of the Robot Operating System project, released under the MIT License. Please
# see the LICENSE file included as part of this package.
#
# author:   Murray Altheim
# created:  2021-02-25
# modified: 2021-02-25
#

import pytest
import sys, time, traceback
from colorama import init, Fore, Style
init()

from lib.fan import Fan
from lib.logger import Level
from lib.config_loader import ConfigLoader
from lib.logger import Logger, Level

# ..............................................................................
@pytest.mark.unit
def test_fan():
    _fan = None
    _log = Logger("fan test", Level.INFO)
    try:
        # read YAML configuration
        _loader = ConfigLoader(Level.INFO)
        filename = 'config.yaml'
        _config = _loader.configure(filename)
        _fan = Fan(_config, Level.INFO)

        limit = 2
        for i in range(limit):
            _log.info('Switching fan on!  [{:d}/{:d}]'.format(i+1,limit))
            _fan.enable()
            time.sleep(5)
            _log.info('Switching fan off! [{:d}/{:d}]'.format(i+1,limit))
            _fan.disable()
            time.sleep(5)

    except KeyboardInterrupt:
        _log.info("Disabling switch")
        if _fan:
            _fan.disable()
    except Exception as e:
        _log.error('error in fan: {}\n{}'.format(e, traceback.format_exc()))
        sys.exit(1)

# ..............................................................................
def main():
    try:
        test_fan()
    except KeyboardInterrupt:
        print(Fore.CYAN + 'Ctrl-C caught: complete.')
    except Exception as e:
        print(Fore.RED + 'error closing: {}\n{}'.format(e, traceback.format_exc()))

if __name__== "__main__":
    main()

#EOF
