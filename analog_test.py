#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# Copyright 2020-2021 by Murray Altheim. All rights reserved. This file is part
# of the Robot Operating System project, released under the MIT License. Please
# see the LICENSE file included as part of this package.
#
# author:   Murray Altheim
# created:  2020-03-16
# modified: 2021-03-25
#

import pytest
import sys, time, itertools, traceback
from colorama import init, Fore, Style
init()

from lib.logger import Logger, Level
from lib.analog import AnalogInput

# ..............................................................................
@pytest.mark.unit
def test_analog():

    _log = Logger("analog test", Level.INFO)

    try:

        _log.info('creating analog input...')
        _analog = AnalogInput(Level.INFO)
        _counter = itertools.count()

        _log.info(Fore.RED + 'Press Ctrl+C to exit.')
        while True:
            _count = next(_counter)
            _voltages = _analog.read()
            _log.info(Fore.GREEN + Style.BRIGHT + '[{:03d}] channel 0: {:5.2f}V; channel 1: {:5.2f}V; channel 2: {:5.2f}V.'.format(\
                    _count, _voltages[0], _voltages[1], _voltages[2]))
            time.sleep(1.0)

    except KeyboardInterrupt:
        print(Fore.RED + 'Ctrl-C caught: complete.')
    except Exception as e:
        print(Fore.RED + 'error closing: {}\n{}'.format(e, traceback.format_exc()))

    _log.info('complete.')

# ..............................................................................
def main():
    test_analog()

if __name__== "__main__":
    main()

#EOF
