#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# Copyright 2020 by Murray Altheim. All rights reserved. This file is part of
# the Robot Operating System project and is released under the "Apache Licence, 
# Version 2.0". Please see the LICENSE file included as part of this package.
#

import sys, math
from colorama import init, Fore, Style
init()

from lib.logger import Level, Logger
from lib.convert import Convert

# ..............................................................................

_log = Logger('convert', Level.INFO)

# .............................................................................................
def test_offset(angle, offset, expected):
    _log.header('Rotate Test','{:5.2f}°, offset {:5.2f}°, expected {:5.2f}°'.format(angle, offset, expected),'1/3')
    result = Convert.offset_in_degrees(angle, offset)
    if not math.isclose(result, expected):
        _log.error('expected {:5.2f}°, not {:5.2f}°\n'.format(expected, result))

    # now radians...
    result2 = Convert.to_degrees(Convert.offset_in_radians(Convert.to_radians(angle), Convert.to_radians(offset)))
    if not math.isclose(result2, expected):
        _log.error('expected {:5.2f}°, not {:5.2f}°\n'.format(expected, result2))
    _log.info(Fore.GREEN + 'result:\t{:>5.2f}°'.format(result))
    _log.info('')


# main .........................................................................
def main(argv):

    test_offset(330.0, 70.0, 40.0)
    test_offset(350.0, 15.0, 5.0)
    test_offset(360.0, -10.0, 350.0)
    test_offset(270.0, -70.0, 200.0)

    _log.info('complete.')

# call main ....................................................................
if __name__== "__main__":
    main(sys.argv[1:])

#EOF
