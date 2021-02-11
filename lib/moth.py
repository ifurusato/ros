#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# Copyright 2020 by Murray Altheim. All rights reserved. This file is part
# of the pimaster2ardslave project and is released under the MIT Licence;
# please see the LICENSE file included as part of this package.
#
# author:   Murray Altheim
# created:  2021-02-12
# modified: 2021-02-12
#

from colorama import init, Fore, Style
init()

from lib.enums import Orientation
from lib.logger import Logger, Level
from lib.ioe import IoExpander

class Moth(object):
    '''
    A "moth" behaviour is where the robot moves towards the brightest light; an "anti-moth"
    behaviour towards the darker area of its environment.

    Captures the two analog outputs from the IO Expander used for moth and anti-moth sensing.
    returning pairs of int and float values, an Orientation enum, or a bias ratio between
    -max and +max. The int and float values are determined by the actual sensor outputs, with
    the int values rounded up and multiplied by 100. So if the sensor output at maximum light
    intensity is 3.3v the raw value would be 3.3 and the int value would be 330.

    There is a hysteresis configuration that sets the range within which the port-starboard
    bias is considered nil.

    The actual sensor used can be any analog light sensor that outputs a floating value. On
    the KD01/KR01 robots this happens to be a pair of Adafruit GA1A12S202 Log-scale Analog
    Light Sensors, aiming forward, port and starboard at about 45 degrees.

    :param config:  the application configuration
    :param ioe:     the optional IO Expander. If not supplied one will be created from the
                    provided configuration.
    :param level:   the log level
    '''
    def __init__(self, config, ioe, level):
        if config is None:
            raise ValueError('no configuration provided.')
        _config = config['ros'].get('moth')
        self._hysteresis = _config.get('hysteresis')
        self._log = Logger("moth", level)
        if ioe:
            self._ioe = ioe
        else:
            self._ioe = IoExpander(config, Level.INFO)
        self._log.info('ready.')

    # ..........................................................................
    @property
    def ioe(self):
        '''
        Return the IO Expander used by the Moth sensor.
        '''
        return self._ioe

    def get_orientation(self):
        '''
        Processes the two sensor inputs, returning Orientation.PORT,
        Orientation.STBD, or Orientation.NONE when there is no bias.
        The hysteresis determining the range of "no bias" is set in
        configuration.
        '''
        _values = self._ioe.get_moth_values()
        if _values[0] > _values[1] + self._hysteresis:
            self._log.info(Fore.RED + Style.BRIGHT    + 'Orientation.PORT:\t'
                    + Fore.RED + Style.NORMAL + '{:d}\t'.format(_values[0]) + Fore.GREEN + '{:d}'.format(_values[1]))
            return Orientation.PORT
        elif _values[0] < _values[1] - self._hysteresis:
            self._log.info(Fore.GREEN + Style.BRIGHT  + 'Orientation.STBD:\t'
                    + Fore.RED + Style.NORMAL + '{:d}\t'.format(_values[0]) + Fore.GREEN + '{:d}'.format(_values[1]))
            return Orientation.STBD
        else:
            self._log.info(Fore.YELLOW + Style.BRIGHT + 'Orientation.NONE:\t'
                    + Fore.RED + Style.NORMAL + '{:d}\t'.format(_values[0]) + Fore.GREEN + '{:d}'.format(_values[1]))
            return Orientation.NONE

    def get_int_values(self):
        '''
        Return the values of the port and starboard moth sensors
        (resp.) as a two-element array, in the range 0-MAX, where
        MAX is likely 330.
        '''
        return self._ioe.get_moth_values()

    def get_values(self):
        '''
        Return the values of the port and starboard moth sensors
        (resp.) as a two-element array, in the range 0.0-MAX_V,
        where MAX_V is likely 3.3v.
        '''
        return self._ioe.get_raw_moth_values()

    def get_bias(self):
        '''
        Returns a value from -MAX_V (port) to +MAX_V (starboard), with
        zero as no rotational bias. There is no hysteresis in the result.
        '''
        _values = self._ioe.get_raw_moth_values()
        return ( -1.0 * _values[0] ) + _values[1]

#EOF
