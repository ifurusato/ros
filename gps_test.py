#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# Copyright 2020-2021 by Murray Altheim. All rights reserved. This file is part
# of the Robot Operating System project, released under the MIT License. Please
# see the LICENSE file included as part of this package.
#
# author:   Murray Altheim
# created:  2021-03-06
# modified: 2021-03-06
#

import pytest
import sys, time, traceback
from colorama import init, Fore, Style
init()

from lib.logger import Level
from lib.gps import GPS

# ..............................................................................
@pytest.mark.unit
def test_gps():

    _gps = GPS(Level.INFO)
    while True:
        _gps.read()
        _gps.display()
        time.sleep(1.0)

# ..............................................................................
def main():

    try:
        test_gps()
    except KeyboardInterrupt:
        print(Fore.CYAN + 'Ctrl-C caught: complete.' + Style.RESET_ALL)
        sys.exit(0)
    except Exception as e:
        print(Fore.RED + 'error closing: {}\n{}'.format(e, traceback.format_exc()) + Style.RESET_ALL)
        sys.exit(1)

if __name__== "__main__":
    main()

#EOF
