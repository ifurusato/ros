#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# Copyright 2020 by Murray Altheim. All rights reserved. This file is part of
# the Robot Operating System project and is released under the "Apache Licence,
# Version 2.0". Please see the LICENSE file included as part of this package.
#
# author:   Murray Altheim
# created:  2020-11-13
# modified: 2020-11-13
#

import colorsys
import ioexpander as io
from colorama import init, Fore, Style
init()

from lib.logger import Logger

# ..............................................................................
class RotaryEncoder(object):

    '''
    Suppports a rotary encoder provided with an RGB LED for feedback. 

    Change the I2C_ADDR to:
     - 0x0F to use with the Rotary Encoder breakout.
     - 0x18 to use with IO Expander.
    
    Press Ctrl+C to exit.
    '''
    def __init__(self, config, level):
        super().__init__()
        self._log = Logger("rot", level)
        if config is None:
            raise ValueError('null configuration argument.')
        _config          = config['ros'].get('rotary_encoder')
        _i2c_address     = _config.get('i2c_address')
        self._brightness = _config.get('brightness') # effectively the maximum fraction of the period that the LED will be on
        self._log.info("configured for I²C address of 0x{:02x}".format(_i2c_address))

#       _i2c_address     = 0x0F  # 0x18 for IO Expander, 0x0F for the encoder breakout
#       _i2c_address     = 0x18    # 0x19 for IO Expander, 0x0F for the encoder breakout
        _i2c_address     = 0x19  # TEMP
#       _i2c_address     = 0x20  # TEMP
#       _new_i2c_address = 0x16
        self._ioe = io.IOE(i2c_addr=_i2c_address, interrupt_pin=4)

        # swap the interrupt pin for the Rotary Encoder breakout
#       if I2C_ADDR == 0x0F:
        self._ioe.enable_interrupt_out(pin_swap=True)
        # change address to 
#       if I2C_ADDR != _new_i2c_address:
#       self._ioe.set_i2c_addr(_new_i2c_address)
        
        _POT_ENC_A = 12
        _POT_ENC_B = 3
        _POT_ENC_C = 11
        self._ioe.setup_rotary_encoder(1, _POT_ENC_A, _POT_ENC_B, pin_c=_POT_ENC_C)

        self._period    = int(255 / self._brightness)  # add a period large enough to get 0-255 steps at the desired brightness
        self._log.info("running LED with {} brightness steps.".format(int(self._period * self._brightness)))
        self._ioe.set_pwm_period(self._period)
        self._ioe.set_pwm_control(divider=2)  # PWM as fast as we can to avoid LED flicker
        
        self._pin_red   = 1
        self._pin_green = 7
        self._pin_blue  = 2
        self._ioe.set_mode(self._pin_red,   io.PWM, invert=True)
        self._ioe.set_mode(self._pin_green, io.PWM, invert=True)
        self._ioe.set_mode(self._pin_blue,  io.PWM, invert=True)

        self._count = 0
        self._log.info('ready.')

    # ..........................................................................
    def update(self):
        '''
        Updates the encoder and returns the current value.
        '''
#       r, g, b, = 0, 0, 0
        if self._ioe.get_interrupt():
            self._count = self._ioe.read_rotary_encoder(1) # argument is channel
            self._ioe.clear_interrupt()
        h = (self._count % 360) / 360.0
        r, g, b = [int(c * self._period * self._brightness) for c in colorsys.hsv_to_rgb(h, 1.0, 1.0)]
        self._ioe.output(self._pin_red,   r)
        self._ioe.output(self._pin_green, g)
        self._ioe.output(self._pin_blue,  b)
        self._log.info('RGB: {},{},{}'.format(r, g, b) + Fore.YELLOW + '\tvalue: {:d}'.format(self._count))
        return self._count

    # ..........................................................................
    def reset(self):
        '''
        Clears the count value and sets the RGB LED to black (off).
        '''
        self._count = 0
        self._ioe.output(self._pin_red,   0)
        self._ioe.output(self._pin_green, 0)
        self._ioe.output(self._pin_blue,  0)
        self._log.info('reset.')


#EOF
