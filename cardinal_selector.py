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

from lib.i2c_scanner import I2CScanner
from lib.config_loader import ConfigLoader
from lib.rate import Rate
from lib.enums import Cardinal, Color
from lib.logger import Logger, Level
from lib.rotary_encoder import RotaryEncoder

# ..............................................................................
def get_color_for_direction(value):
    if value is Cardinal.NORTH:
        return Color.BLUE
    elif value is Cardinal.NORTHEAST:
        return Color.CYAN
    elif value is Cardinal.EAST:
        return Color.GREEN
    elif value is Cardinal.SOUTHEAST:
        return Color.YELLOW_GREEN
    elif value is Cardinal.SOUTH:
        return Color.YELLOW
    elif value is Cardinal.SOUTHWEST:
        return Color.ORANGE
    elif value is Cardinal.WEST:
        return Color.RED
    elif value is Cardinal.NORTHWEST:
        return Color.MAGENTA
    else:
        return Color.BLACK

# ..............................................................................
@pytest.mark.unit
def test_rot_encoder():

    _log = Logger("rot-test", Level.INFO)

    _i2c_scanner = I2CScanner(Level.WARN)
    if not _i2c_scanner.has_address([0x19]):
        _log.warning('test ignored: no rotary encoder found.')
        return

    try:
        # read YAML configuration
        _loader = ConfigLoader(Level.INFO)
        filename = 'config.yaml'
        _config = _loader.configure(filename)
        _rot = RotaryEncoder(_config, Level.INFO)
        _rot.increment = 9

        _count      = 0
        _updates    = 0
        _update_led = False
        _last_value = 0
        _rate = Rate(20)
        _log.info(Fore.WHITE + Style.BRIGHT + 'live-updating rotary encoder...')
        while True:
#           _value = _rot.update() # original method
            _value = _rot.read(_update_led) % 360 # improved method
            if _value != _last_value:
                _cardinal = Cardinal.get_heading_from_degrees(_value)
                _color = get_color_for_direction(_cardinal)
                _log.info(Style.BRIGHT + 'returned value: {:d}; cardinal: {}; color: {}'.format(_value, _cardinal, _color))
                _rot.set_led((int(_color.red), int(_color.green), int(_color.blue)))
                _updates += 1
            _last_value = _value
            _count += 1
            if _count % 33 == 0:
                _log.info(Fore.BLACK + Style.BRIGHT + 'waiting…')
            _rate.wait()
    finally:
        if _rot:
            _log.info('resetting rotary encoder...')
            _rot.reset()

# main .........................................................................
_rot = None
def main(argv):

    try:
        test_rot_encoder()
    except KeyboardInterrupt:
        print(Fore.CYAN + 'caught Ctrl-C; exiting...' + Style.RESET_ALL)
    except Exception:
        print(Fore.RED + 'error starting ros: {}'.format(traceback.format_exc()) + Style.RESET_ALL)


# call main ....................................................................
if __name__== "__main__":
    main(sys.argv[1:])

#EOF
