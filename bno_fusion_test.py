#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# Copyright 2020-2021 by Murray Altheim. All rights reserved. This file is part
# of the Robot Operating System project, released under the MIT License. Please
# see the LICENSE file included as part of this package.
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
from lib.enums import Cardinal
from lib.bno08x import BNO08x
from lib.bno055 import BNO055

_bno = None

# ..............................................................................
@pytest.mark.unit
def test_bno08x():

    _log = Logger('fusion', Level.INFO)
    _loader = ConfigLoader(Level.INFO)
    filename = 'config.yaml'
    _config = _loader.configure(filename)

    _message_factory = MessageFactory(Level.INFO)
    _queue = MessageQueue(_message_factory, Level.INFO)
    _bno08x = BNO08x(_config, _queue, Level.INFO)
    _bno055 = BNO055(_config, _queue, Level.INFO)

    while True:
        _bno08x_heading = _bno08x.read()
        _mag_degrees    = _bno08x_heading[0] if _bno08x_heading is not None else 0.0

        _bno055_result = _bno055.read()
        _calibration = _bno055_result[0]
        _bno055_heading = _bno055_result[1]
        if _calibration.calibrated:
            _mag_diff  = _bno055_heading - _mag_degrees
            _log.info(Fore.BLUE + Style.BRIGHT + 'heading: {:>6.2f}°\t(bno085)\t'.format(_mag_degrees) + Style.DIM + 'diff: {:>5.2f}°;\ttrim: {:>5.2f}°'.format(_mag_diff, _bno08x.heading_trim))
            _log.info(Fore.CYAN + Style.BRIGHT + 'heading: {:>6.2f}°\t(bno055)'.format(_bno055_heading))
            _cardinal = Cardinal.get_heading_from_degrees(_bno055_heading)
            _log.info(Fore.WHITE + Style.BRIGHT + 'cardinal:  \t{}\n'.format(_cardinal.display.lower()))

#           _log.info('')

#       _log.info(Fore.BLACK + '.' + Style.RESET_ALL)
        time.sleep(2.0)

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
