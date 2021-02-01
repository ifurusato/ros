#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# Copyright 2020 by Murray Altheim. All rights reserved. This file is part of
# the Robot Operating System project and is released under the "Apache Licence,
# Version 2.0". Please see the LICENSE file included as part of this package.
#
# author:   Murray Altheim
# created:  2020-11-13
# modified: 2020-11-13
#

import pytest
import sys, traceback
from colorama import init, Fore, Style
init()

from lib.config_loader import ConfigLoader
from lib.rate import Rate
from lib.logger import Logger, Level
from lib.rotary_ctrl import RotaryControl

# ..............................................................................
@pytest.mark.unit
def test_rot_control():

    _log = Logger("rot-ctrl-test", Level.INFO)

    _rot_ctrl = None
    try:
        # read YAML configuration
        _loader = ConfigLoader(Level.INFO)
        filename = 'config.yaml'
        _config = _loader.configure(filename)

      # def __init__(self, config, minimum, maximum, step, level):
#       _min  = -127
#       _max  = 127
#       _step = 1

        _min  = 0
        _max  = 10
        _step = 0.5
        _rot_ctrl = RotaryControl(_config, _min, _max, _step, Level.INFO)

        _rate = Rate(20)
        _log.info(Fore.WHITE + Style.BRIGHT + 'waiting for changes to rotary encoder...')

        while True:
            _value = _rot_ctrl.read() 
            _log.info(Fore.YELLOW + ' value: {:d}'.format(_value))
            _rate.wait()

    finally:
        if _rot_ctrl:
            _log.info('resetting rotary encoder...')
            _rot_ctrl.reset()

# main .........................................................................
_rot = None
def main(argv):

    try:
        test_rot_control()
    except KeyboardInterrupt:
        print(Fore.CYAN + 'caught Ctrl-C; exiting...' + Style.RESET_ALL)
    except Exception:
        print(Fore.RED + 'error starting ros: {}'.format(traceback.format_exc()) + Style.RESET_ALL)


# call main ....................................................................
if __name__== "__main__":
    main(sys.argv[1:])

#EOF
