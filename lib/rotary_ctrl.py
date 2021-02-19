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

import os.path
from colorama import init, Fore, Style
init()

from lib.logger import Logger, Level
from lib.rotary_encoder import RotaryEncoder

# ..............................................................................
class RotaryControl(object):
    '''
    Uses an RGB Encoder Breakout as a potentiometer, where rotating the
    shaft clockwise increases the returned value by a given step, counter-
    clockwise by the negative value of the step. This is clipped between
    minimum and maximum limits. 
    '''
    def __init__(self, config, minimum, maximum, step, level):
        self._log = Logger("rot-ctrl", level)
        if config is None:
            raise ValueError('no configuration provided.')
        _config = config['ros'].get('rotary_ctrl')
        # configuration ....................
        self._min         = minimum
        self._max         = maximum
        self._step        = step
#       if True or os.path.isfile('/dev/i2c-1'): # are we on a Pi?
        _i2c_address      = _config.get('i2c_address')
#       _i2c_address      = 0x0F
        self._log.info('configured rotary control at I²C address: 0x{:02X}'.format(_i2c_address))
        self._update_led  = _config.get('update_led')
        self._log.info('update LED: {}'.format(self._update_led))
        self._log.info('min: {:5.2f}; max: {:5.2f}; step: {:5.2f}'.format(self._min, self._max, self._step))
        self._rot = RotaryEncoder(config, _i2c_address, level)
#       else:
#           self._rot = None 
#           self._log.warning('disabled: no I²C support.')
        self._value       = -1.0
        self._last_delta  = 0.0

    # ..........................................................................
    def read(self):
        if self._rot:
            _delta = self._rot.read(self._update_led)
            print('_delta: {}'.format(_delta))
#           if _delta != self._last_delta:
            if _delta > self._last_delta: # if increasing in value
                self._value = RotaryControl.clamp(self._value + self._step, self._min, self._max) 
            elif _delta < self._last_delta: # if decreasing in value
                self._value = RotaryControl.clamp(self._value - self._step, self._min, self._max)
#           self._log.info(Style.DIM + 'delta: {:5.2f} (last: {:5.2f});'.format(_delta, self._last_delta) + Fore.WHITE + Style.NORMAL + ' value: {:5.2f}'.format(self._value))
            self._last_delta = _delta
        return self._value

    # ..........................................................................
    @staticmethod
    def clamp(n, minn, maxn):
        return max(min(maxn, n), minn)

    # ..........................................................................
    def reset(self):
        if self._rot:
            self._rot.reset()

#EOF
