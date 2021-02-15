#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# Copyright 2020 by Murray Altheim. All rights reserved. This file is part of
# the Robot OS project and is released under the "Apache Licence, Version 2.0".
# Please see the LICENSE file included as part of this package.
#
# author:   altheim
# created:  2020-01-18
# modified: 2020-10-28
#
# Wraps the functionality of a Pimoroni IO Expander Breakout board, providing
# access to the values of the board's pins, which outputs 0-255 values for
# analog pins, and a 0 or 1 for digital pins.
#
# source: /usr/local/lib/python3.7/dist-packages/ioexpander/__init__.py
#

import sys
import ioexpander as io
from colorama import init, Fore, Style
init()

from lib.logger import Logger, Level
from lib.event import Event

# ..............................................................................
class MockIoe(object):

    def __init__(self, trigger_pin, level):
        self._log = Logger('mock-ioe', level)
        self._trigger_pin = trigger_pin
        self._active_value = 0.60
        self._value = 0.0
        self._log.info('ready.')

    def set_default_value(self, value):
        self._value = value

    def input(self, pin):
        if pin == self._trigger_pin:
            self._log.info(Fore.YELLOW + 'returning triggerd value {:5.2f} for pin {:d}.'.format(self._active_value, pin))
            return self._active_value
        else:
            self._log.info(Style.DIM + 'returning mock value 0.0 for pin {:d}.'.format(pin))
            return self._value

# ..............................................................................
class MockIoExpander():
    '''
    A mock of an IO Expander board.
    '''
    def __init__(self, config, level):
        super().__init__()
        if config is None:
            raise ValueError('no configuration provided.')
        _config = config['ros'].get('io_expander')
        self._log = Logger('mock-io-expander', level)
        # infrared
        self._port_side_ir_pin = _config.get('port_side_ir_pin')  # pin connected to port side infrared
        self._port_ir_pin      = _config.get('port_ir_pin')       # pin connected to port infrared
        self._center_ir_pin    = _config.get('center_ir_pin')     # pin connected to center infrared
        self._stbd_ir_pin      = _config.get('stbd_ir_pin')       # pin connected to starboard infrared
        self._stbd_side_ir_pin = _config.get('stbd_side_ir_pin')  # pin connected to starboard side infrared
        self._log.info('infrared pin assignments:\t' \
                + Fore.RED + ' port side={:d}; port={:d};'.format(self._port_side_ir_pin, self._port_ir_pin) \
                + Fore.BLUE + ' center={:d};'.format(self._center_ir_pin) \
                + Fore.GREEN + ' stbd={:d}; stbd side={:d}'.format(self._stbd_ir_pin, self._stbd_side_ir_pin))
        # moth/anti-moth
        self._port_moth_pin    = _config.get('port_moth_pin')     # pin connected to port moth sensor
        self._stbd_moth_pin    = _config.get('stbd_moth_pin')     # pin connected to starboard moth sensor
        self._log.info('moth pin assignments:\t' \
                + Fore.RED + ' moth port={:d};'.format(self._port_moth_pin) \
                + Fore.GREEN + ' moth stbd={:d};'.format(self._stbd_moth_pin))
        # bumpers
        self._port_bmp_pin     = _config.get('port_bmp_pin')      # pin connected to port bumper
        self._cntr_bmp_pin     = _config.get('center_bmp_pin')    # pin connected to center bumper
        self._stbd_bmp_pin     = _config.get('stbd_bmp_pin')      # pin connected to starboard bumper
        self._log.info('bumper pin assignments:\t' \
                + Fore.RED + ' port={:d};'.format(self._port_bmp_pin) \
                + Fore.BLUE + ' center={:d};'.format(self._cntr_bmp_pin) \
                + Fore.GREEN + ' stbd={:d}'.format(self._stbd_bmp_pin))
        # configure board
        self._ioe = MockIoe(self._center_ir_pin, level)
        self._port_bmp_pump = 0
        self._cntr_bmp_pump = 0
        self._stbd_bmp_pump = 0
        self._pump_limit    = 10
        self._log.info('ready.')

    # infrared sensors .........................................................

    def get_port_side_ir_value(self):
        return int(round(self._ioe.input(self._port_side_ir_pin) * 100.0))

    def get_port_ir_value(self):
        return int(round(self._ioe.input(self._port_ir_pin) * 100.0))

    def get_center_ir_value(self):
        return int(round(self._ioe.input(self._center_ir_pin) * 100.0))

    def get_stbd_ir_value(self):
        return int(round(self._ioe.input(self._stbd_ir_pin) * 100.0))

    def get_stbd_side_ir_value(self):
        return int(round(self._ioe.input(self._stbd_side_ir_pin) * 100.0))

    # moth/anti-moth ...........................................................

    def get_moth_values(self):
        return [ int(round(self._ioe.input(self._port_moth_pin) * 100.0)), \
                 int(round(self._ioe.input(self._stbd_moth_pin) * 100.0)) ]

    # bumpers ..................................................................

    def get_port_bmp_value(self):
        return ( self._ioe.input(self._port_bmp_pin) == 0 )
#       return ( self._ioe.input(self._port_bmp_pin) == 0 )

    def get_center_bmp_value(self):
        _value = self._ioe.input(self._cntr_bmp_pin)
        if _value == 0:
            print(Fore.GREEN + 'get_center_bmp_value({}): {}'.format(type(_value), _value) + Style.RESET_ALL)
            return True
        else:
            print(Fore.RED + 'get_center_bmp_value({}): {}'.format(type(_value), _value) + Style.RESET_ALL)
            return False
#       return ( _value == 0 )
#       return ( self._ioe.input(self._cntr_bmp_pin) == 0 )

    def get_stbd_bmp_value(self):
        return ( self._ioe.input(self._stbd_bmp_pin) == 0 )
#       return ( self._ioe.input(self._stbd_bmp_pin) == 0 )

    # ..........................................................................
    # raw values are unprocessed values from the IO Expander (used for testing)
   
    # raw infrared sensors .....................................................

    def get_raw_port_side_ir_value(self):
        return self._ioe.input(self._port_side_ir_pin)

    def get_raw_port_ir_value(self):
        return self._ioe.input(self._port_ir_pin)

    def get_raw_center_ir_value(self):
        return self._ioe.input(self._center_ir_pin)

    def get_raw_stbd_ir_value(self):
        return self._ioe.input(self._stbd_ir_pin)

    def get_raw_stbd_side_ir_value(self):
        return self._ioe.input(self._stbd_side_ir_pin)

    # raw moth sensors .........................................................

    def get_raw_moth_values(self):
        return [ self._ioe.input(self._port_moth_pin), self._ioe.input(self._stbd_moth_pin) ]

    def get_raw_port_moth_value(self):
        return self._ioe.input(self._port_moth_pin)

    def get_raw_stbd_moth_value(self):
        return self._ioe.input(self._stbd_moth_pin)

    # raw bumpers ..............................................................

    def get_raw_port_bmp_value(self):
        return self._ioe.input(self._port_bmp_pin)

    def get_raw_center_bmp_value(self):
        return self._ioe.input(self._cntr_bmp_pin)

    def get_raw_stbd_bmp_value(self):
        return self._ioe.input(self._stbd_bmp_pin)


# EOF
