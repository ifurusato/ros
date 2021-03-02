#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# Copyright 2020-2021 by Murray Altheim. All rights reserved. This file is part
# of the Robot Operating System project, released under the MIT License. Please
# see the LICENSE file included as part of this package.
#
# created:  2020-10-05
# modified: 2020-10-05
#

import sys, time, traceback
import board
from colorama import init, Fore, Style
init()

try:
    from adafruit_ina260 import INA260, AveragingCount
except ImportError:
    sys.exit("This script requires the adafruit_ina260 module\nInstall with: pip3 install --user adafruit_ina260")

from lib.logger import Logger, Level

class CurrentSensor(object):
    '''
    Supports a pair of current sensors based on the Adafruit INA260, as typically attached
    to a port/starboard pair of motors. This reads current in milliamps, voltage in volts,
    and power in milliwatts, returning the property-style values as tuples.

    See also:

      Product Page: 
          https://www.adafruit.com/product/4226
      User Guide:
          https://learn.adafruit.com/adafruit-ina260-current-voltage-power-sensor-breakout
      TI INA260 Documentation:
          http://www.ti.com/lit/ds/symlink/ina260.pdf
    '''
    def __init__(self, config, level=Level.INFO):
        if config is None:
            raise ValueError('null configuration argument.')
        self._log = Logger('current', level)
        _config = config['ros'].get('current')
        self._port_address = _config.get('port_address')
        self._stbd_address = _config.get('stbd_address') 
        self._log.info('INA260 addresses: ' + Fore.RED + 'port: 0x{:02X}; '.format(self._port_address) + Fore.GREEN + 'starboard: 0x{:02X}'.format(self._stbd_address))
        i2c = board.I2C()
        self._ina260_port = INA260(i2c, address=self._port_address)
        _averaging_count = AveragingCount.COUNT_4  # 1 (default), 4. 16, 128, 256, 512, 1024
        self._ina260_port.averaging_count = _averaging_count
        self._ina260_stbd = INA260(i2c, address=self._stbd_address)
        self._ina260_stbd.averaging_count = _averaging_count
        self._log.info('ready.')

    # ..........................................................................
    @property
    def current(self):
        '''
        Return the current in milliamps, as a port/starboard tuple.
        '''
        _current_port = self._ina260_port.current
        _current_stbd = self._ina260_stbd.current
        self._log.debug('current:\t' + Fore.RED + '{:<7}{:>7.2f}mA;\t'.format('port:', _current_port) + Fore.GREEN + '{:<7}{:>7.2f}mA'.format('stbd:', _current_stbd))
        return [_current_port, _current_stbd ]

    # ..........................................................................
    @property
    def voltage(self):
        '''
        Return the voltage in volts, as a port/starboard tuple.
        '''
        _voltage_port = self._ina260_port.voltage 
        _voltage_stbd = self._ina260_stbd.voltage
        self._log.debug('voltage:\t' + Fore.RED + '{:<7}{:>8.2f}V; \t'.format('port:', _voltage_port) + Fore.GREEN + '{:<7}{:>8.2f}V'.format('stbd:', _voltage_stbd))
        return [_voltage_port, _voltage_stbd]

    # ..........................................................................
    @property
    def power(self):
        '''
        Return the power in milliwatts, as a port/starboard tuple.
        '''
        _power_port = self._ina260_port.power
        _power_stbd = self._ina260_stbd.power
        self._log.debug('power:  \t' + Fore.RED + '{:<7}{:>7.2f}mW;\t'.format('port:', _power_port) + Fore.GREEN + '{:<7}{:>7.2f}mW'.format('stbd:', _power_stbd))
        return [_power_port, _power_stbd]

#EOF
