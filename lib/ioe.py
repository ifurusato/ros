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

import ioexpander as io
from colorama import init, Fore, Style
init()

from lib.logger import Logger, Level
from lib.event import Event

# ..............................................................................
class IoExpander():
    '''
    Wraps an IO Expander board as input from an integrated front sensor
    array of infrareds and bumper switches.
    '''

    def __init__(self, config, level):
        super().__init__()
        if config is None:
            raise ValueError('no configuration provided.')
        _config = config['ros'].get('io_expander')
        self._log = Logger('ioe', level)
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
        # bumpers
        self._port_bmp_pin     = _config.get('port_bmp_pin')      # pin connected to port bumper
        self._cntr_bmp_pin     = _config.get('center_bmp_pin')    # pin connected to center bumper
        self._stbd_bmp_pin     = _config.get('stbd_bmp_pin')      # pin connected to starboard bumper
        self._log.info('bumper pin assignments:\t' \
                + Fore.RED + ' port={:d};'.format(self._port_bmp_pin) \
                + Fore.BLUE + ' center={:d};'.format(self._cntr_bmp_pin) \
                + Fore.GREEN + ' stbd={:d}'.format(self._stbd_bmp_pin))

        # configure board
        self._ioe = io.IOE(i2c_addr=0x18)
#       self._ioe.set_i2c_addr(0x18)
        self._ioe.set_adc_vref(3.3)  # input voltage of IO Expander, this is 3.3 on Breakout Garden
        # debouncing "charge pumps"
        self._port_bmp_pump = 0
        self._cntr_bmp_pump = 0
        self._stbd_bmp_pump = 0
        self._pump_limit    = 10
        # analog infrared sensors
        self._ioe.set_mode(self._port_side_ir_pin, io.ADC)
        self._ioe.set_mode(self._port_ir_pin,      io.ADC)
        self._ioe.set_mode(self._center_ir_pin,    io.ADC)
        self._ioe.set_mode(self._stbd_ir_pin,      io.ADC)
        self._ioe.set_mode(self._stbd_side_ir_pin, io.ADC)
        # digital bumpers
        self._ioe.set_mode(self._port_bmp_pin,     io.IN_PU)
        self._ioe.set_mode(self._cntr_bmp_pin,     io.IN_PU)
        self._ioe.set_mode(self._stbd_bmp_pin,     io.IN_PU)
        self._log.info('ready.')

    # ..........................................................................
    def add(self, message):
        '''
        React to every 5th TICK message.
        '''
#       self._log.info(Fore.YELLOW + Style.DIM + 'MESSAGE received at message {:d}.'.format(message.eid))
        if message.event is Event.CLOCK_TICK:
            if message.eid % 5 == 0:
#               self._log.info(Fore.GREEN + Style.BRIGHT + 'STBD bumper: {}'.format(self._ioe.input(self._stbd_bmp_pin)))
                if self._ioe.input(self._port_bmp_pin) == 0:
                    self._port_bmp_pump = self._pump_limit
                if self._ioe.input(self._cntr_bmp_pin) == 0:
                    self._cntr_bmp_pump = self._pump_limit
                if self._ioe.input(self._stbd_bmp_pin) == 0:
                    self._stbd_bmp_pump = self._pump_limit
            else:
                if self._port_bmp_pump > 0:
                    self._port_bmp_pump -= 1
                if self._cntr_bmp_pump > 0:
                    self._cntr_bmp_pump -= 1
                if self._stbd_bmp_pump > 0:
                    self._stbd_bmp_pump -= 1
            self._log.debug('message[{:d}] received values: '.format(message.eid) \
                    + Fore.RED   + 'PORT={:d}\t'.format(self._port_bmp_pump) \
                    + Fore.BLUE  + 'CNTR={:d}\t'.format(self._cntr_bmp_pump) \
                    + Fore.GREEN + 'STBD={:d}'.format(self._stbd_bmp_pump) )
        pass

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

    # bumpers ..................................................................

    def get_port_bmp_value(self):
#       return self._port_bmp_pump > 0
        return self._ioe.input(self._port_bmp_pin) == 0

    def get_center_bmp_value(self):
#       return self._cntr_bmp_pump > 0
        return self._ioe.input(self._cntr_bmp_pin) == 0

    def get_stbd_bmp_value(self):
#       return self._stbd_bmp_pump > 0
        return self._ioe.input(self._stbd_bmp_pin) == 0

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

    # raw bumpers ..............................................................



    def get_raw_port_bmp_value(self):
        return self._ioe.input(self._port_bmp_pin)

    def get_raw_center_bmp_value(self):
        return self._ioe.input(self._cntr_bmp_pin)

    def get_raw_stbd_bmp_value(self):
        return self._ioe.input(self._stbd_bmp_pin)


# EOF
