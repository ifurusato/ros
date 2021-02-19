#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# Copyright 2020 by Murray Altheim. All rights reserved. This file is part
# of the pimaster2ardslave project and is released under the MIT Licence;
# please see the LICENSE file included as part of this package.
#
# author:   Murray Altheim
# created:  2020-04-30
# modified: 2020-05-24
#
# This tests the two GA1A12S202 Log-scale Analog Light Sensors connected
# as a port and starboard "moth" sensor. The pair of analog signals are
# returned via a Pimoroni IO Expander Breakout Garden board, an I²C-based
# microcontroller.
#

import pytest
import time, traceback
from colorama import init, Fore, Style
init()

from lib.enums import Orientation
from lib.logger import Logger, Level
from lib.config_loader import ConfigLoader
from lib.moth import Moth
from lib.rgbmatrix import RgbMatrix, Color, DisplayType


# ..............................................................................
@pytest.mark.unit
def test_moth():
    '''
    Test the basic functionality of the Moth sensor's various outputs.
    The test is entirely visual, i.e., something to be looked at, tested
    with a bright light source.
    '''
    _log = Logger("test", Level.INFO)
    # read YAML configuration
    _loader = ConfigLoader(Level.INFO)
    filename = 'config.yaml'
    _config = _loader.configure(filename)
    _moth = Moth(_config, None, Level.INFO)

    _rgbmatrix = RgbMatrix(Level.INFO)
    _rgbmatrix.set_display_type(DisplayType.SOLID)

#   for i in range(50):
    while True:
        # orientation and bias .............................
        _orientation = _moth.get_orientation()
        _bias = _moth.get_bias()
        _log.debug('bias: {}; orientation: {}'.format(type(_bias), _orientation))
        if _orientation is Orientation.PORT:
            _rgbmatrix.show_color(Color.BLACK, Orientation.STBD)
            _rgbmatrix.show_color(Color.RED, Orientation.PORT)
            _log.info(Fore.RED    + Style.BRIGHT + '{}\t {:<6.3f}'.format(_orientation.name, _bias[0]))
        elif _orientation is Orientation.STBD:
            _rgbmatrix.show_color(Color.BLACK, Orientation.PORT)
            _rgbmatrix.show_color(Color.GREEN, Orientation.STBD)
            _log.info(Fore.GREEN  + Style.BRIGHT + '{}\t {:<6.3f}'.format(_orientation.name, _bias[1]))
        else:
            _rgbmatrix.show_color(Color.YELLOW, Orientation.PORT)
            _rgbmatrix.show_color(Color.YELLOW, Orientation.STBD)
            _log.info(Fore.YELLOW + '{}\t {:6.3f}|{:6.3f}'.format(_orientation.name, _bias[0], _bias[1]))
        # int values .......................................
        _int_values = _moth.get_int_values()
        _log.info(Fore.RED   + '{:d}\t'.format(_int_values[0]) + Fore.GREEN + '{:d}\t'.format(_int_values[1]) )
        # float values .....................................
        _values = _moth.get_values()
        _log.info(Fore.RED   + '{:<6.3f}\t'.format(_values[0]) + Fore.GREEN + '{:<6.3f}\t'.format(_values[1]) )
#       time.sleep(1.0)
        time.sleep(0.1)

# ..............................................................................
def main():
    try:
        test_moth()
    except KeyboardInterrupt:
        print(Fore.RED + 'Ctrl-C caught; exiting...' + Style.RESET_ALL)
    except Exception as e:
        print(Fore.RED + Style.BRIGHT + 'error testing ifs: {}\n{}'.format(e, traceback.format_exc()) + Style.RESET_ALL)

if __name__== "__main__":
    main()

#EOF
