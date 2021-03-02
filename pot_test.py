#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# Copyright 2020-2021 by Murray Altheim. All rights reserved. This file is part
# of the Robot Operating System project, released under the MIT License. Please
# see the LICENSE file included as part of this package.
#
# author:   Murray Altheim
# created:  2020-09-19
# modified: 2020-09-19
#

import pytest
import sys, traceback
from colorama import init, Fore, Style
init()

from lib.config_loader import ConfigLoader
from lib.logger import Logger, Level
from lib.rate import Rate
from lib.pot import Potentiometer

_log = Logger('pot-test', Level.INFO)

# ..............................................................................
@pytest.mark.unit
def test_pot():
    '''
    Tests reading the wiper of a potentiometer attached to a GPIO pin,
    where its other two connections are to Vcc and ground.
    '''
    _loader = ConfigLoader(Level.INFO)
    filename = 'config.yaml'
    _config = _loader.configure(filename)

    _pot = Potentiometer(_config, Level.DEBUG)

    _value = 0
    # start...
    _rate = Rate(20) # Hz
#   i = 0
#   while True:
    for i in range(20):
        _value        = _pot.get_value()
        _scaled_value = _pot.get_scaled_value()
        _log.info('[{:d}] analog value: {:03d};'.format(i, _value) + Fore.GREEN + '\tscaled: {:>7.4f};'.format(_scaled_value))
        _rate.wait()
#   assert _value != 0

# main .........................................................................
def main(argv):

    try:
        test_pot()
    except KeyboardInterrupt:
        _log.info('caught Ctrl-C; exiting...')
    except Exception:
        _log.error('error starting potentiometer: {}'.format(traceback.format_exc()))

# call main ....................................................................
if __name__== "__main__":
    main(sys.argv[1:])

#EOF
