#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# Copyright 2020 by Murray Altheim. All rights reserved. This file is part of
# the Robot Operating System project and is released under the "Apache Licence,
# Version 2.0". Please see the LICENSE file included as part of this package.
#
# author:   Murray Altheim
# created:  2021-01-02
# modified: 2021-01-03
#
# ..............................................................................
# Provides a six-position selector with colored knob indicator for each of the
# 60 degree quadrants, e.g., red is -30 through 30 degrees.
#
#           R
#
#       M       Y
#
#       B       G
#
#           C
#
# This uses an RGB Encoder Breakout board from the Pimoroni Breakout Garden series.
#

from lib.enums import Color
from lib.logger import Logger, Level
from lib.rotary_encoder import RotaryEncoder

# ..............................................................................
class Selector(object):

    def __init__(self, config, level):
        if config is None:
            raise ValueError('no configuration provided.')
        self._log = Logger("selector", level)
        self._rot = RotaryEncoder(config, i2c_address=0x0F, level=Level.WARN)
        self._rot.increment = 8
        self._last_value    = 0
        self._colors = [ Color.RED, Color.YELLOW, Color.GREEN, Color.CYAN, Color.BLUE, Color.MAGENTA ]
        self._log.info('ready.')

    # ..........................................................................
    def read(self):
        _value = self._rot.read(False) % 360
        if _value != self._last_value:
            _color = self.get_color_for_heading(_value)
            self._rot.set_led((int(_color.red), int(_color.green), int(_color.blue)))
            self._log.info('returned value: {:d}; color: {}'.format(_value, _color))
        self._last_value = _value
        return _value

    # ..........................................................................
    def get_color_for_heading(self, degrees):
        '''
        Provided a heading in degrees return a color.
        '''
        _value = round(((degrees-30.0) / 60.0) + 0.5)
        _index = (_value % 6)
        _color = self._colors[_index]
        self._log.debug('{}°; value: {}; index: {}; color: {}'.format(degrees, _value, _index, _color))
        return _color

    # ..........................................................................
    def reset(self):
        _color = Color.BLACK
        self._rot.set_led((int(_color.red), int(_color.green), int(_color.blue)))
        self._rot.reset()
        self._log.info('reset.')

#EOF
