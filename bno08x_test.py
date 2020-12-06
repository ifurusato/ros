#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# Copyright 2020 by Murray Altheim. All rights reserved. This file is part of
# the Robot Operating System project and is released under the "Apache Licence,
# Version 2.0". Please see the LICENSE file included as part of this package.
#
# author:   Murray Altheim
# created:  2020-03-27
# modified: 2020-03-27
#
# https://www.adafruit.com/product/4754
# https://learn.adafruit.com/adafruit-9-dof-orientation-imu-fusion-breakout-bno085
# https://learn.adafruit.com/adafruit-9-dof-orientation-imu-fusion-breakout-bno085/report-types
# https://www.ceva-dsp.com/wp-content/uploads/2019/10/BNO080_085-Datasheet.pdf
# https://circuitpython.readthedocs.io/projects/bno08x/en/latest/
#
import pytest
import sys, time
from colorama import init, Fore, Style
init()

from lib.logger import Level, Logger
from lib.config_loader import ConfigLoader
from lib.message_factory import MessageFactory
from lib.queue import MessageQueue

from lib.bno08x import BNO08x

_bno = None

# ..............................................................................
@pytest.mark.unit
def test_bno08x():
    _loader = ConfigLoader(Level.INFO)
    filename = 'config.yaml'
    _config = _loader.configure(filename)

    _message_factory = MessageFactory(Level.INFO)
    _queue = MessageQueue(_message_factory, Level.INFO)
    _bno = BNO08x(_config, _queue, Level.INFO)

    # begin ............
    _bno.enable()
    print(Fore.CYAN + 'wave robot in air until it beeps...' + Style.RESET_ALL)
    while True:
        _bno.read()
        print(Fore.BLACK + '.' + Style.RESET_ALL)
        time.sleep(1.0)

# ..............................................................................
def main():

    try:
        test_bno08x()
    except KeyboardInterrupt:
        if _bno:
            _bno.close()
        print('done.')

if __name__== "__main__":
    main()

#EOF
