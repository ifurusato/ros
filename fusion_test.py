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
# Fusion here means combining the heading outputs of the BNO055 and BNO085.
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
from lib.compass import Compass

_bno08x = None

# ..............................................................................
@pytest.mark.unit
def test_fusion():

    _log = Logger('fusion', Level.INFO)
    _loader = ConfigLoader(Level.INFO)
    filename = 'config.yaml'
    _config = _loader.configure(filename)

    _message_factory = MessageFactory(Level.INFO)
    _queue = MessageQueue(_message_factory, Level.INFO)
    _bno08x = BNO08x(_config, _queue, Level.INFO)
    _compass = Compass(_config, _queue, None, Level.WARN)
    _compass.enable()

    # begin ............
    _bno08x.enable()
    _log.info('wave robot in air until it beeps...')
    while True:
        _bno08x_heading = _bno08x.read()
        # _mag_degrees, _quaternion, _geomagnetic_quaternion
        _mag_degrees    = _bno08x_heading[0] if _bno08x_heading is not None else 0.0
        _quaternion     = _bno08x_heading[1] if _bno08x_heading is not None else 0.0
        _geo_quaternion = _bno08x_heading[2] if _bno08x_heading is not None else 0.0

        _result = _compass.get_heading()
        _calibration = _result[0]
        _heading = _result[1]
        if _calibration.calibrated:
            _mag_diff  = _heading - _mag_degrees    
            _quat_diff = _heading - _quaternion    
            _geo_diff  = _heading - _geo_quaternion
#           _log.info(Fore.CYAN + Style.BRIGHT + 'bno\theading: {:>5.2f}°\t'.format(_heading) + Style.DIM + 'mag diff: {}°\tquat diff: {}°\tgeo diff: {}°'.format(type(_mag_diff), type(_quat_diff), type(_geo_diff)))
            _log.info(Fore.CYAN + Style.BRIGHT + 'heading\tbno055: {:>5.2f}° / bno085: {:>5.2f}°\t'.format(_heading, _mag_degrees) \
                    + Style.DIM + 'diffs: mag: {:>5.2f}°\tquat: {:>5.2f}°\tgeo: {:>5.2f}°'.format(_mag_diff, _quat_diff, _geo_diff))

        else:
            _log.info(Fore.BLACK   + 'bno055\theading: {:>5.2f}°'.format(_heading))
#       _log.info(Fore.BLACK + '.')
        time.sleep(1.0)

# ..............................................................................
def main():

    try:
        test_fusion()
    except KeyboardInterrupt:
        if _bno08x:
            _bno08x.close()
        print('done.')

if __name__== "__main__":
    main()

#EOF
