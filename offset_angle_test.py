#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# Copyright 2020 by Murray Altheim. All rights reserved. This file is part of
# the Robot Operating System project and is released under the "Apache Licence, 
# Version 2.0". Please see the LICENSE file included as part of this package.
#
# A sanity check for our heading conversion/offset. This makes no assertions;
# its output is meant to be read on the console.
#

import pytest
import sys, time, math
from numpy import arange
from colorama import init, Fore, Style
init()

from lib.logger import Level, Logger
from lib.convert import Convert

# ..............................................................................
@pytest.mark.unit
def test_offset():
    _log = Logger('test-offset', Level.INFO)
    _test_offset(_log, 330.0, 70.0, 40.0)
    _test_offset(_log, 350.0, 15.0, 5.0)
    _test_offset(_log, 360.0, -10.0, 350.0)
    _test_offset(_log, 270.0, -70.0, 200.0)
    _log.info('complete.')

# ..............................................................................
@pytest.mark.unit
def _test_offset(log, angle, offset, expected):
    log.header('Rotate Test','{:5.2f}°, offset {:5.2f}°, expected {:5.2f}°'.format(angle, offset, expected),'1/4')
    result = Convert.offset_in_degrees(angle, offset)
    if not math.isclose(result, expected):
        log.error('expected {:5.2f}°, not {:5.2f}°\n'.format(expected, result))

    # now radians...
    result2 = Convert.to_degrees(Convert.offset_in_radians(Convert.to_radians(angle), Convert.to_radians(offset)))
    if not math.isclose(result2, expected):
        log.error('expected {:5.2f}°, not {:5.2f}°\n'.format(expected, result2))
    log.info(Fore.GREEN + 'result:\t{:>5.2f}°'.format(result))

# ..............................................................................
@pytest.mark.unit
def test_offset_rotate():
    _log = Logger("offset-rotate-test", Level.INFO)
    _count = 0
    for offset in arange(0.0, 360.0, 90.0):
        _count += 1
        _log.header('Offset Rotate Test', 'offset={:<5.2f};'.format(offset), '{:d}/4'.format(_count))
        for angle in arange(0.0, 360.0, 30.0):
            _alt = Convert.offset_in_degrees(angle, offset)
            _log.info(Fore.GREEN + 'from {:>5.2f}°\tto {:>5.2f}°;'.format(angle, _alt) + Fore.BLACK + '\toffset={:<5.2f};'.format(offset))
            time.sleep(0.01)
    _log.info('complete.')

# main .........................................................................
def main(argv):
    test_offset()
    test_offset_rotate()

# call main ....................................................................
if __name__== "__main__":
    main(sys.argv[1:])

#EOF
