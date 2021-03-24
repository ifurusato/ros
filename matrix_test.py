#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# Copyright 2020-2021 by Murray Altheim. All rights reserved. This file is part
# of the Robot Operating System project, released under the MIT License. Please
# see the LICENSE file included as part of this package.
#
# This tests the 11x7 Matrix, including several custom modes.
#

import pytest
import sys, time
from colorama import init, Fore, Style
init()

from lib.logger import Logger, Level
from lib.i2c_scanner import I2CScanner
from lib.enums import Orientation
from lib.matrix import Matrix

# ..............................................................................
@pytest.mark.unit
def test_matrix():

    _port_light = None
    _stbd_light = None

    _log = Logger('matrix-test', Level.INFO)

    try:

        _log.info(Fore.CYAN + 'start matrix test...')   
        
        _i2c_scanner = I2CScanner(Level.DEBUG)
        if _i2c_scanner.has_address([0x77]): # port
            _port_light = Matrix(Orientation.PORT, Level.INFO)
            _log.info('port-side matrix available.')
        else:
            _log.warning('no port-side matrix available.')
        if _i2c_scanner.has_address([0x75]): # starboard
            _stbd_light = Matrix(Orientation.STBD, Level.INFO)
            _log.info('starboard-side matrix available.')
        else:
            _log.warning('no starboard-side matrix available.')

        if not _port_light and not _stbd_light:
            _log.warning('skipping test: no matrix displays available.')
            return

        if _port_light:
            _port_light.text('Y', False, False)
        if _stbd_light:
            _stbd_light.text('N', False, False)
        time.sleep(2)

        if _port_light:
            _port_light.disable()
            _port_light.clear()
        if _stbd_light:
            _stbd_light.disable()
            _stbd_light.clear()
        time.sleep(1)

        _log.info('matrix on...')   
        if _port_light:
            _port_light.light()
        if _stbd_light:
            _stbd_light.light()
        time.sleep(2)

        if _port_light:
            _port_light.clear()
        if _stbd_light:
            _stbd_light.clear()
        time.sleep(1)

        _log.info('matrix gradient...')   
        for x in range(3):
            for i in range(1,8):
                _log.info('matrix at {:d}'.format(i))   
                if _port_light:
                    _port_light.gradient(i)
                if _stbd_light:
                    _stbd_light.gradient(i)
                time.sleep(0.01)
            if _port_light:
                _port_light.clear()
            if _stbd_light:
                _stbd_light.clear()
            time.sleep(0.1)

    except KeyboardInterrupt:
        _log.info(Fore.MAGENTA + 'Ctrl-C caught: interrupted.')
    finally:
        _log.info('closing matrix test...')   
        if _port_light:
            _port_light.clear()
        if _stbd_light:
            _stbd_light.clear()


# call main ......................................

def main():

    test_matrix()

if __name__== "__main__":
    main()

