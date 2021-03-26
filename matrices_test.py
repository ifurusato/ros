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
from lib.matrix import Matrices

# ..............................................................................
@pytest.mark.unit
def test_matrix():

    _log = Logger('matrix-test', Level.INFO)
    _matrices = None

    try:

        _log.info(Fore.CYAN + 'start matrices test...')   
        
        _matrices = Matrices(Level.INFO)

        _matrices.text('Y', 'N')
        time.sleep(2)

        _matrices.clear()
#       if _port_light:
#           _port_light.disable()
#           _port_light.clear()
#       if _stbd_light:
#           _stbd_light.disable()
#           _stbd_light.clear()
        time.sleep(1)

        _log.info('matrix on...')   
        _matrices.on()
        time.sleep(2)

        _log.info('matrix off...')   
        _matrices.clear()
        time.sleep(1)

        _log.info('starting matrix blink_on...')   
        _matrices.blink(True, 0.00)
        time.sleep(0.0)
        _matrices.blink(False, 0.00)
        _matrices.clear()


    except KeyboardInterrupt:
        _log.info(Fore.MAGENTA + 'Ctrl-C caught: interrupted.')
    finally:
        _log.info('closing matrix test...')   
        if _matrices:
            _matrices.clear()


# call main ......................................

def main():

    test_matrix()

if __name__== "__main__":
    main()

