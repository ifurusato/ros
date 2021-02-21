#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# Copyright 2020 by Murray Altheim. All rights reserved. This file is part of
# the Robot Operating System project and is released under the "Apache Licence,
# Version 2.0". Please see the LICENSE file included as part of this package.
#
# author:   Murray Altheim
# created:  2020-05-19
# modified: 2020-11-06
#
# dd mock IFS that responds to key presses
#

import sys, time, traceback
from colorama import init, Fore, Style
init()
try:
    import pytest
except ImportError:
    sys.exit(Fore.RED + "This script requires the pytest module.\nInstall with: pip3 install --user pytest" + Style.RESET_ALL)

from mock.ifs import MockIntegratedFrontSensor
from lib.logger import Logger, Level

# ..............................................................................
@pytest.mark.unit
def test_mock_ifs():
    _log = Logger('mock-ifs-test', Level.INFO)
    time.sleep(1.0)
    _ifs = MockIntegratedFrontSensor(Level.INFO)
    _ifs.enable()
    while _ifs.enabled:
        time.sleep(1.0)
    _ifs.close()
    _log.info('test complete.')

# ..............................................................................
def main():

    try:
        test_mock_ifs()
    except KeyboardInterrupt:
        print(Fore.RED + 'Ctrl-C caught; exiting...' + Style.RESET_ALL)
    except Exception as e:
        print(Fore.RED + Style.BRIGHT + 'error starting ifs: {}\n{}'.format(e, traceback.format_exc()) + Style.RESET_ALL)
    finally:
        pass

if __name__== "__main__":
    main()

#EOF
