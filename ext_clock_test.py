#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# Copyright 2020-2021 by Murray Altheim. All rights reserved. This file is part
# of the Robot Operating System project, released under the MIT License. Please
# see the LICENSE file included as part of this package.
#
# author:   Murray Altheim
# created:  2021-02-19
# modified: 2021-02-19
#
# Uses an interrupt (event detect) set on a GPIO pin as an external Clock trigger.
#

import pytest
import sys, time
from colorama import init, Fore, Style
init()

from lib.config_loader import ConfigLoader
from lib.logger import Logger, Level
from lib.message_bus import MessageBus
from lib.ext_clock import ExternalClock

# ..............................................................................
@pytest.mark.unit
def test_external_clock():

    _log = Logger("xclock", Level.INFO)
    _log.info('starting test...')

    # read YAML configuration
    _loader = ConfigLoader(Level.INFO)
    filename = 'config.yaml'
    _config = _loader.configure(filename)

    _message_bus = MessageBus(Level.INFO)
    _clock = ExternalClock(_config, _message_bus, Level.INFO)

    try:
        _log.info('starting clock...')
        _clock.enable()
        while True:
            time.sleep(1.0)
    except KeyboardInterrupt:
        _log.info("caught Ctrl-C.")
    finally:
        _log.info("closed.")

# main .........................................................................

def main(argv):
    test_external_clock()

# call main ....................................................................
if __name__== "__main__":
    main(sys.argv[1:])

#EOF
