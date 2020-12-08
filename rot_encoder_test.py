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
from lib.rotary_encoder import RotaryEncoder

# ..............................................................................
@pytest.mark.unit
def test_rot_encoder(log):
    try:
        # read YAML configuration
        _loader = ConfigLoader(Level.INFO)
        filename = 'config.yaml'
        _config = _loader.configure(filename)
        _rot = RotaryEncoder(_config, Level.INFO)

        _count      = 0
        _updates    = 0
        _update_led = True
        _last_value = 0
        _rate = Rate(20)
        log.info(Fore.WHITE + Style.BRIGHT + 'waiting for rotary encoder to make 10 ticks...')
        while _updates < 10:
#           _value = _rot.update() # original method
            _value = _rot.read(_update_led) # improved method
            if _value != _last_value:
                log.info(Style.BRIGHT + 'returned value: {:d}'.format(_value))
                _updates += 1
            _last_value = _value
            _count += 1
            if _count % 33 == 0:
                log.info(Fore.BLACK + Style.BRIGHT + 'waiting…')
            _rate.wait()
    finally:
        if _rot:
            log.info('resetting rotary encoder...')
            _rot.reset()

# main .........................................................................
_rot = None
def main(argv):

    _log = Logger("rot-test", Level.INFO)
    try:
        test_rot_encoder(_log)
    except KeyboardInterrupt:
        _log.info('caught Ctrl-C; exiting...')
    except Exception:
        _log.error('error starting ros: {}'.format(traceback.format_exc()))


# call main ....................................................................
if __name__== "__main__":
    main(sys.argv[1:])

#EOF
