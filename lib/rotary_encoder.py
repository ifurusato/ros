#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# Copyright 2020-2021 by Murray Altheim. All rights reserved. This file is part
# of the Robot Operating System project, released under the MIT License. Please
# see the LICENSE file included as part of this package.
#
# author:   Murray Altheim
# created:  2020-11-13
# modified: 2020-11-13
#

import sys, colorsys, traceback
from colorama import init, Fore, Style
init()

try:
    import ioexpander as io
except ImportError:
    print(Fore.RED + "This script requires the pimoroni-ioexpander module\nInstall with: pip3 install --user pimoroni-ioexpander" + Style.RESET_ALL)

from lib.logger import Logger, Level

# ..............................................................................
class RotaryEncoder(object):
    '''
    Supports a rotary encoder provided with an RGB LED for feedback.
    Not to be confused with a motor encoder.

    Change the I2C_ADDR to:
     - 0x0F to use with the Rotary Encoder breakout.
     - 0x18 to use with IO Expander.

    :param config:       application-level configuration
    :param level:        log level
    '''
    def __init__(self, config, level=Level.INFO):
        super().__init__()
        self._log = Logger("rot", level)
        if config is None:
            raise ValueError('null configuration argument.')
        _config = config['ros'].get('rotary_encoder')
        self._brightness  = _config.get('brightness') # effectively the maximum fraction of the period that the LED will be on
        self._log.info("brightness:\t{:5.2f}".format(self._brightness))
        self.increment    = _config.get('increment')  # the count change per rotary tick
        _i2c_address      = _config.get('i2c_address')
#       self._log.info("I²C address:\t0x{:02x}".format(_i2c_address))
        self._log.info('configured rotary encoder at I²C address: 0x{:02X}'.format(_i2c_address))

#       _i2c_address = 0x0f # found via i2cdetect
#       self._log.info("default I²C address:  0x{:02X}".format(I2C_ADDR))
#       self._log.info("assigned I²C address: 0x{:02X}".format(_i2c_address))

        try:
#           _i2c_address  = 0x16
            _i2c_address  = 0x0F  # 0x18 for IO Expander, 0x0F for the encoder breakout
#           _i2c_address  = 0x18  # 0x19 for IO Expander, 0x0F for the encoder breakout
            self._ioe     = io.IOE(i2c_addr=_i2c_address, interrupt_pin=4)
            # swap the interrupt pin for the Rotary Encoder breakout
            self._ioe.enable_interrupt_out(pin_swap=True)
#           if I2C_ADDR != _i2c_address:
#               self._log.warning("force-setting I²C address of 0x{:02X}".format(_i2c_address))
#               self._ioe.set_i2c_addr(_i2c_address)

            _POT_ENC_A = 12
            _POT_ENC_B = 3
            _POT_ENC_C = 11
            self._ioe.setup_rotary_encoder(1, _POT_ENC_A, _POT_ENC_B, pin_c=_POT_ENC_C) #, count_microsteps=False)

            self._period = int(255 / self._brightness) # add a period large enough to get 0-255 steps at the desired brightness
            self._log.info("running LED with {} brightness steps.".format(int(self._period * self._brightness)))
            self._ioe.set_pwm_period(self._period)
            self._ioe.set_pwm_control(divider=2)  # PWM as fast as we can to avoid LED flicker

            self._channel   = 1
            self._pin_red   = 1
            self._pin_green = 7
            self._pin_blue  = 2
            self._ioe.set_mode(self._pin_red,   io.PWM, invert=True)
            self._ioe.set_mode(self._pin_green, io.PWM, invert=True)
            self._ioe.set_mode(self._pin_blue,  io.PWM, invert=True)

            # reset IOE values on start
            self.reset()

        except Exception as e:
            self._log.error('error configuring rotary encoder: {}\n{}'.format(e, traceback.format_exc()))
            sys.exit(1)

        self._count = 0
        self._log.info('ready.')

    # ..........................................................................
    @property
    def increment(self):
        '''
        Return the increment count used to alter the output value per tick.
        '''
        return self._increment

    # ..........................................................................
    @increment.setter
    def increment(self, increment):
        '''
        Set the increment count used to alter the output value per tick.
        '''
        self._log.info("increment set to {:d}.".format(increment))
        self._increment = increment

    # ..........................................................................
    def update(self):
        '''
        Updates the encoder and returns the current value, setting the RGB LED
        color based on the count modulo 360.

        This is the original example method and suprisingly doesn't start at a
        value of zero, but remembers the last value from the IO Expander. Use
        read() for a more expected behaviour.
        '''
        if self._ioe.get_interrupt():
            self._count = self._ioe.read_rotary_encoder(self._channel)
            self._ioe.clear_interrupt()
        self._set_led()
        return self._count

    # ..........................................................................
    def read(self, update_led=True):
        '''
        Updates the encoder and returns the current value, by default modifying
        the RGB LED. If 'update_led' is False the RGB LED will not be updated
        as part of the call.
        '''
        if self._ioe.get_interrupt():
            _last   = self._ioe._encoder_last[self._channel - 1]
            _offset = self._ioe._encoder_offset[self._channel - 1]
            self._log.info(Fore.BLUE + 'last:  {:>3d};\t'.format(_last) + Style.DIM + 'offset: {:d}'.format(_offset))
            _value  = self._ioe.read_rotary_encoder(self._channel)
            _diff = _last - _value
            # initial value may be non-zero
            if _diff > 1:
                _diff = 1
            elif _diff < -1:
                _diff = -1
            self._count -= _diff * self._increment # minus so that clockwise increases value
            if update_led:
                self._set_led()
            self._log.info('count: {:>3d};\t'.format(self._count) + Fore.BLACK + 'value: {:>3d};\t'.format(_value) + Style.DIM + 'diff: {:d}'.format(_diff) )
            self._ioe.clear_interrupt()
        return self._count

    # ..........................................................................
    def _set_led(self):
        '''
        Set the RGB LED color based on the value of the internal count, modulo 360.
        '''
        h = (self._count % 360) / 360.0
        r, g, b = [int(c * self._period * self._brightness) for c in colorsys.hsv_to_rgb(h, 1.0, 1.0)]
        self.set_led((r, g, b))
#       self._ioe.output(self._pin_red,   r)
#       self._ioe.output(self._pin_green, g)
#       self._ioe.output(self._pin_blue,  b)
        self._log.debug('RGB: {},{},{}'.format(r, g, b) + Style.DIM + '\tvalue: {:d}'.format(self._count))

    # ..........................................................................
    def set_led(self, color):
        '''
        Set the RGB LED color to the supplied RGB tuple.
        '''
        self._ioe.output(self._pin_red,   color[0])
        self._ioe.output(self._pin_green, color[1])
        self._ioe.output(self._pin_blue,  color[2])

    # ..........................................................................
    def reset(self):
        '''
        Clears the count value and sets the RGB LED to black (off).
        '''
        # reset internal IOE values on start
        self._count = 0
        self._ioe._encoder_last   = [0, 0, 0, 0]
        self._ioe._encoder_offset = [0, 0, 0, 0]
        self._ioe.output(self._pin_red,   0)
        self._ioe.output(self._pin_green, 0)
        self._ioe.output(self._pin_blue,  0)
        self._log.info('reset.')

#EOF
