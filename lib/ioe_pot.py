#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# Copyright 2020 by Murray Altheim. All rights reserved. This file is part
# of the pimaster2ardslave project and is released under the MIT Licence;
# please see the LICENSE file included as part of this package.
#
# author:   Murray Altheim
# created:  2020-09-19
# modified: 2020-09-19
#

import math, sys, traceback, time, colorsys
import ioexpander as io
from colorama import init, Fore, Style
init()

from lib.config_loader import ConfigLoader
from lib.logger import Level, Logger
from lib.rate import Rate

# ..............................................................................
class Potentiometer(object):
    '''
       Configures an IO Expander based potentiometer, returning an analog
       value scaled to a specified range. For a center-zero pot simply
       specify the minimum value as (-1.0 * out_max).
    '''
    def __init__(self, config, level):
        super().__init__()
        self._log = Logger('ioe', level)
        if config is None:
            raise ValueError('no configuration provided.')
        _config = config['ros'].get('ioe_potentiometer')

        # 0x18 for IO Expander, 0x0E for the potentiometer breakout
#       self._i2c_addr = 0x0E
        self._i2c_addr   = _config.get('i2c_address')
        self._pin_red    = _config.get('pin_red')
        self._pin_green  = _config.get('pin_green')
        self._pin_blue   = _config.get('pin_blue')
        self._log.info("pins: red: {}; green: {}; blue: {}".format(self._pin_red, self._pin_green, self._pin_blue))
        
        self._pot_enc_a  = 12
        self._pot_enc_b  = 3
        self._pot_enc_c  = 11
        self._max_value  = 3.3                       # maximum voltage (3.3v supply)
        self._brightness = _config.get('brightness') # effectively max fraction of period LED will be on
        self._period = int(255 / self._brightness)   # add a period large enough to get 0-255 steps at the desired brightness
        
        _in_min = _config.get('in_min')  # minimum analog value from IO Expander 
        _in_max = _config.get('in_max')  # maximum analog value from IO Expander 
        self.set_input_limits(_in_min, _in_max)
        _out_min = _config.get('out_min') # minimum scaled output value
        _out_max = _config.get('out_max') # maximum scaled output value
        self.set_output_limits(_out_min, _out_max)

        # now configure IO Expander
        self._ioe = io.IOE(i2c_addr=self._i2c_addr)
        self._ioe.set_mode(self._pot_enc_a, io.PIN_MODE_PP)
        self._ioe.set_mode(self._pot_enc_b, io.PIN_MODE_PP)
        self._ioe.set_mode(self._pot_enc_c, io.ADC)
        self._ioe.output(self._pot_enc_a, 1)
        self._ioe.output(self._pot_enc_b, 0)
        self._ioe.set_pwm_period(self._period)
        self._ioe.set_pwm_control(divider=2)  # PWM as fast as we can to avoid LED flicker
        self._ioe.set_mode(self._pin_red,   io.PWM, invert=True)
        self._ioe.set_mode(self._pin_green, io.PWM, invert=True)
        self._ioe.set_mode(self._pin_blue,  io.PWM, invert=True)
        
        self._log.info("running LED with {} brightness steps.".format(int(self._period * self._brightness)))
        self._log.info("ready.")

    # ..........................................................................
    def set_input_limits(self, in_min, in_max):
        self._in_min = in_min
        self._in_max = in_max
        self._log.info('input range:\t{:>5.2f}-{:<5.2f}'.format(self._in_min, self._in_max))

    # ..........................................................................
    def set_output_limits(self, out_min, out_max):
        self._out_min = out_min
        self._out_max = out_max
        self._log.info('output range:\t{:>5.2f}-{:<5.2f}'.format(self._out_min, self._out_max))

    # ..........................................................................
    def get_value(self):
        value = self._max_value - self._ioe.input(self._pot_enc_c)
        self._log.debug(Fore.BLACK + 'value: {:<5.2f}'.format(value))
        return value

    # ..........................................................................
    def set_rgb(self, value):
        h = value / self._max_value # time.time() / 10.0
        r, g, b = [int(c * self._period * self._brightness) for c in colorsys.hsv_to_rgb(h, 1.0, 1.0)]
        self._ioe.output(self._pin_red, r)
        self._ioe.output(self._pin_green, g)
        self._ioe.output(self._pin_blue, b)
        self._log.debug('value: {:<5.2f}; rgb: {},{},{}'.format(value, r, g, b))

    # ..........................................................................
    def get_scaled_value(self):
        '''
                   (out_max - out_min)(value - in_min)
            f(x) = -----------------------------------  + out_min
                            in_max - in_min

            where: a = 0.0, b = 1.0, min = 0, max = 330.
        '''
        return (( self._out_max - self._out_min ) * ( self.get_value() - self._in_min ) / ( self._in_max - self._in_min )) + self._out_min

    # ..........................................................................
    def test(self):
        _hz = 10
        _rate = Rate(_hz, Level.ERROR)
        while True:
            _value = self.get_value()
            self.set_rgb(_value)
            _scaled_value = math.floor(self.get_scaled_value()) # as integer
            self._log.info(Fore.YELLOW + 'scaled value: {:d}'.format(_scaled_value) + Style.RESET_ALL)
            _rate.wait()
#           time.sleep(1.0 / 30)

#EOF

