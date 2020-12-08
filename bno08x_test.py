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
def test_bno08x(log, loop):

    _loader = ConfigLoader(Level.INFO)
    filename = 'config.yaml'
    _config = _loader.configure(filename)

    _message_factory = MessageFactory(Level.INFO)
    _queue = MessageQueue(_message_factory, Level.INFO)
    _bno = BNO08x(_config, _queue, Level.INFO)

    # begin ............
    log.info('starting BNO08x read loop...')
    _count = 0
    while _count < 10 if not loop else True:
        _count += 1
        result = _bno.read()
        if result != None:
            log.info('[{:>3d}] result: {:>5.2f} | {:>5.2f} | {:>5.2f} |'.format(_count, result[0], result[1], result[2]))
        else:
            log.warning('[{:>3d}] result: NA'.format(_count))
        time.sleep(0.25)

# ..............................................................................
def main():

    _log = Logger("rot-test", Level.INFO)
    try:
        test_bno08x(_log, True)
    except KeyboardInterrupt:
        if _bno:
            _bno.close()
    finally:
        _log.info('done.')

if __name__== "__main__":
    main()

#EOF
