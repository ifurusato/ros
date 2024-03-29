#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# Copyright 2020-2021 by Murray Altheim. All rights reserved. This file is part
# of the Robot Operating System project, released under the MIT License. Please
# see the LICENSE file included as part of this package.
#
# author:   Murray Altheim
# created:  2021-02-09
# modified: 2021-02-09
#

import pytest
import sys, time
from colorama import init, Fore, Style
init()

from lib.enums import Orientation, Color
from lib.i2c_scanner import I2CScanner
from lib.rgbmatrix import RgbMatrix, Color, DisplayType, WipeDirection
from lib.logger import Logger, Level

# ..............................................................................
@pytest.mark.unit
def test_rgbmatrix(_rgbmatrix):

    _log = Logger("rgbmatrix-test", Level.INFO)

    _i2c_scanner = I2CScanner(Level.WARN)
    if not _i2c_scanner.has_address([0x74, 0x77]):
        _log.warning('test ignored: no rgbmatrix displays found.')
        return

    _log.info('starting test...')
    _rgbmatrix.enable()
    _port_rgbmatrix = _rgbmatrix.get_rgbmatrix(Orientation.PORT)
    _stbd_rgbmatrix = _rgbmatrix.get_rgbmatrix(Orientation.STBD)
    for c in [ Color.RED, Color.GREEN, Color.BLUE ]:
        _rgbmatrix.set_wipe_color(c)
        _rgbmatrix._wipe_vertical(_port_rgbmatrix, WipeDirection.DOWN)
        _rgbmatrix._wipe_vertical(_stbd_rgbmatrix, WipeDirection.DOWN)

#   _log.info('rgbmatrix_test    :' + Fore.CYAN + Style.BRIGHT + ' INFO  : color test...')
#   for color in Color:
#       _rgbmatrix.set_color(color)
#       time.sleep(0.15)
#   _log.info('rgbmatrix_test    :' + Fore.CYAN + Style.BRIGHT + ' INFO  : color test complete.')
    
#   BLINKY  = 1
#   CPU     = 2
#   DARK    = 3
#   RAINBOW = 4
#   RANDOM  = 5
#   SCAN    = 6
#   SWORL   = 7
#   SOLID   = 8
#   _types = [ DisplayType.CPU ]
#   _types = [ DisplayType.SWORL, DisplayType.BLINKY, DisplayType.RAINBOW, DisplayType.RANDOM ]
#    _types = [ DisplayType.RANDOM ]
#   _types = [ DisplayType.WIPE_LEFT ]
    
#    for display_type in _types:
#        _log.info('rgbmatrix_test    :' + Fore.CYAN + Style.BRIGHT + ' INFO  : displaying {}...'.format(display_type.name))
#        _rgbmatrix.set_display_type(display_type)
#        _rgbmatrix.enable()
#        time.sleep(60.0 if len(_types) == 1 else 2.0)
#        _rgbmatrix.disable()
#        count = 0
#        while not _rgbmatrix.is_disabled():
#            count += 1
#            time.sleep(1.0)
#            if count > 5:
#                _log.info('rgbmatrix_test    :' + Fore.RED + Style.BRIGHT + ' INFO  : timeout waiting to disable rgbmatrix thread for {}.'.format(display_type.name))
#                sys.exit(1)
#        _rgbmatrix.set_color(Color.BLACK)
#
#        _log.info('rgbmatrix_test    :' + Fore.CYAN + Style.BRIGHT + ' INFO  : {} complete.'.format(display_type.name))

#   time.sleep(1.0)
    _log.info('rgbmatrix_test    :' + Fore.CYAN + Style.BRIGHT + ' INFO  : test complete.')


# main .........................................................................
def main():
    _rgbmatrix = RgbMatrix(Level.INFO)
    try:
        test_rgbmatrix(_rgbmatrix)
    except KeyboardInterrupt:
        print('rgbmatrix_test    :' + Fore.YELLOW + ' INFO  : Ctrl-C caught: exiting...' + Style.RESET_ALL)
    finally:
        if _rgbmatrix:
            _rgbmatrix.disable()
            _rgbmatrix.close()

if __name__== "__main__":
    main()

#EOF
