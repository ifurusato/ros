#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# Copyright 2020 by Murray Altheim. All rights reserved. This file is part of
# the Robot OS project and is released under the "Apache Licence, Version 2.0".
# Please see the LICENSE file included as part of this package.
#
# This tests the Toggle, which reads the state of the toggle switch.
#

import pytest
import os, sys, signal, time
from colorama import init, Fore, Style
init()

from lib.toggle import Toggle
from lib.logger import Logger, Level

def get_label(state):
    _label = 'on' if state else 'off'
    return _label

_log = Logger("toggle-test", Level.INFO)
_toggle = None

# ..............................................................................
@pytest.mark.unit
def test_toggle():
    _log.info('starting test...')
    _pin = 6
    _toggle = Toggle(_pin, Level.INFO)
    _initial_state = _toggle.state
    while _initial_state == _toggle.state:
        _log.info('waiting for change to toggle switch from' + Fore.YELLOW + ' {}'.format(get_label(_initial_state)) \
                + Fore.CYAN + ' on pin {:d}...'.format(_pin))
        time.sleep(1.0)
    while _initial_state != _toggle.state:
        _log.info('waiting for change to toggle switch from' + Fore.YELLOW + ' {}'.format(get_label(not _initial_state)) \
                + Fore.CYAN + ' on pin {:d}...'.format(_pin))
        time.sleep(1.0)

# main .........................................................................
def main(argv):
    try:
        test_toggle()
    except KeyboardInterrupt:
        _log.info("caught Ctrl-C.")
    finally:
        _log.info("closing toggle switch...")
        if _toggle:
            _toggle.close()

# call main ....................................................................
if __name__== "__main__":
    main(sys.argv[1:])


