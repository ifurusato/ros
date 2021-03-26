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

        _matrices.text('HE', 'LP')
        time.sleep(3)

        _matrices.clear()
        time.sleep(1)

        _log.info('matrix on...')   
        _matrices.on()
        time.sleep(2)

        _log.info('matrix off...')   
        _matrices.clear()
        time.sleep(1)

        _log.info('starting matrix vertical wipe...')   
        _matrices.vertical_wipe(True, 0.00)
        time.sleep(0.0)
        _matrices.vertical_wipe(False, 0.00)
        _matrices.clear()
        time.sleep(1)

        _log.info('starting matrix horizontal wipe...')   
        _matrices.horizontal_wipe(True, 0.00)
        time.sleep(0.0)
        _matrices.horizontal_wipe(False, 0.00)
        _matrices.clear()

        time.sleep(1)



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

