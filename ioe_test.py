#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# Copyright 2020-2021 by Murray Altheim. All rights reserved. This file is part
# of the Robot Operating System project, released under the MIT License. Please
# see the LICENSE file included as part of this package.
#
# author:   Murray Altheim
# created:  2020-04-30
# modified: 2020-05-24
#
# This tests the five infrared sensors and three bumper sensors of the
# KR01's Integrated Front Sensor (IFS). Its signals are returned via a
# Pimoroni IO Expander Breakout Garden board, an I²C-based microcontroller.
#

import pytest
import time, traceback
from colorama import init, Fore, Style
init()

from lib.logger import Logger, Level
from lib.config_loader import ConfigLoader
from lib.ioe import IoExpander

# ..............................................................................
@pytest.mark.unit
def test_ioe():
    '''
    Test the basic functionality of the IO Expander's connections to the IR
    and bumper sensors.
    '''
    _log = Logger("test-ioe", Level.INFO)

    # read YAML configuration
    _loader = ConfigLoader(Level.INFO)
    filename = 'config.yaml'
    _config = _loader.configure(filename)
    _ioe = IoExpander(_config, Level.INFO)
    assert _ioe is not None

    _show_ir  = True
    _show_bmp = True

    _bmp_port_triggered = False
    _bmp_cntr_triggered = False
    _bmp_stbd_triggered = False

    for i in range(100000):
        # infrared sensors .........................................................
        if _show_ir:
            _ir_port_side_value = _ioe.get_raw_port_side_ir_value() 
            _ir_port_value      = _ioe.get_raw_port_ir_value()
            _ir_cntr_value      = _ioe.get_raw_center_ir_value() 
            _ir_stbd_value      = _ioe.get_raw_stbd_ir_value()
            _ir_stbd_side_value = _ioe.get_raw_stbd_side_ir_value()
            _log.info(Fore.RED   + 'IR {:8.5f}\t'.format(_ir_port_side_value) \
                                 + '{:8.5f}\t'.format(_ir_port_value) \
                    + Fore.BLUE  + '{:8.5f}\t'.format(_ir_cntr_value) \
                    + Fore.GREEN + '{:8.5f}\t'.format(_ir_stbd_value) \
                                 + '{:8.5f}'.format(_ir_stbd_side_value))
#       # bumpers ..................................................................
        if _show_bmp:
            _bmp_port_value     = _ioe.get_raw_port_bmp_value()
            if _bmp_port_value == 0:
                _bmp_port_triggered = True
            _bmp_cntr_value     = _ioe.get_raw_center_bmp_value()
            if _bmp_cntr_value == 0:
                _bmp_cntr_triggered = True
            _bmp_stbd_value     = _ioe.get_raw_stbd_bmp_value()
            if _bmp_stbd_value == 0:
                _bmp_stbd_triggered = True
#           _log.info(Fore.RED   + 'BMP {}\t'.format(_bmp_port_value) \
#                   + Fore.BLUE  + '{}\t'.format(_bmp_cntr_value) \
#                   + Fore.GREEN + '{}'.format(_bmp_stbd_value))
            _log.info(Fore.RED   + 'BMP Triggered? {}\t'.format(_bmp_port_triggered) \
                    + Fore.BLUE  + '{}\t'.format(_bmp_cntr_triggered) \
                    + Fore.GREEN + '{}'.format(_bmp_stbd_triggered))
        _log.info('i={:d}\n'.format(i))
        time.sleep(0.33)

# ..............................................................................
def main():

    try:
        test_ioe()
    except KeyboardInterrupt:
        print(Fore.RED + 'Ctrl-C caught; exiting...' + Style.RESET_ALL)
    except Exception as e:
        print(Fore.RED + Style.BRIGHT + 'error testing ifs: {}\n{}'.format(e, traceback.format_exc()) + Style.RESET_ALL)

if __name__== "__main__":
    main()

#EOF
