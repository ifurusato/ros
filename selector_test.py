#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# Copyright 2020 by Murray Altheim. All rights reserved. This file is part of
# the Robot Operating System project and is released under the "Apache Licence,
# Version 2.0". Please see the LICENSE file included as part of this package.
#
# author:   Murray Altheim
# created:  2021-01-02
# modified: 2021-01-02
#
# Provides a six-position selector with colored knob indicator for each of 
# the 60 degree quadrants.
#
#           R
#
#       M       Y
#
#       B       G
#
#           C
#

import pytest
import sys, traceback
from colorama import init, Fore, Style
init()

from lib.i2c_scanner import I2CScanner
from lib.config_loader import ConfigLoader
from lib.rate import Rate
from lib.logger import Logger, Level
from lib.selector import Selector

# ..............................................................................
@pytest.mark.unit
def test_selector():

    _log = Logger("sel-test", Level.INFO)
#   _i2c_scanner = I2CScanner(Level.WARN)
#   if not _i2c_scanner.has_address([0x0F]):
#       _log.warning('test ignored: no rotary encoder found.')
#       return

    _selector = None

    try:
        # read YAML configuration
        _loader = ConfigLoader(Level.INFO)
        filename = 'config.yaml'
        _config = _loader.configure(filename)
        _selector   = Selector(_config, Level.INFO)
        _count      = 0
        _updates    = 0
        _rate       = Rate(20)
        _last_value = 0
        _limit      = 45
        _log.info('live-updating from rotary encoder...')
        while _updates < _limit:
            _value = _selector.read()
            if _value != _last_value:
                _updates += 1
                _log.info(Style.BRIGHT + 'returned value: {:d}; updates remaining: {:d}'.format(_value, _limit - _updates))
            else:
                _log.info(Style.DIM    + 'returned value: {:d}; updates remaining: {:d}'.format(_value, _limit - _updates))
            _last_value = _value
            _count += 1
            if _count % 33 == 0:
                _log.info('waiting…')
            _rate.wait()

    finally:
        if _selector:
            _selector.reset()

# main .........................................................................
_rot = None
def main(argv):

    try:
        test_selector()
    except KeyboardInterrupt:
        print(Fore.CYAN + 'caught Ctrl-C; exiting...' + Style.RESET_ALL)
    except Exception:
        print(Fore.RED + 'error starting ros: {}'.format(traceback.format_exc()) + Style.RESET_ALL)


# call main ....................................................................
if __name__== "__main__":
    main(sys.argv[1:])

#EOF
