#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# Copyright 2021 by Murray Altheim. All rights reserved. This file is part of
# the Robot OS project and is released under the "Apache Licence, Version 2.0".
# Please see the LICENSE file included as part of this package.
#
# author:   Murray Altheim
# created:  2021-02-25
# modified: 2021-02-25
#

from ht0740 import HT0740
from lib.logger import Logger, Level
from colorama import init, Fore, Style
init()

class Fan(object):
    '''
    Uses an HT0740 switch to turn a cooling fan on or off.
    '''
    def __init__(self, config, level):
        self._log = Logger("fan", level)
        if config is None:
            raise ValueError('no configuration provided.')
        _config = config['ros'].get('fan')
        _i2c_address     = _config.get('i2c_address')
        self._setpoint   = _config.get('setpoint')
        self._hysteresis = _config.get('hysteresis')
        self._log.info('setpoint temperature: {:5.2f}°C; hysteresis: {:2.1f}°C.'.format(self._setpoint, self._hysteresis))
        self._switch = HT0740(i2c_addr=0x39)
        self._log.info('enabling fan.')
        self._switch.enable()
        self._enabled = False 
        self._log.info('ready.')

    # ..........................................................................
    def react_to_temperature(self, temperature):
        '''
        Performs typical thermostat behaviour:
        * If the CPU temperature is higher than the setpoint plus hysteresis, turn the fan on.
        * If the CPU temperature is lower than the setpoint minus hysteresis, turn the fan off.
        '''
        if temperature > ( self._setpoint + self._hysteresis ):
            if self.enable():
                self._log.info(Fore.YELLOW + 'enable fan:  cpu temperature: {:5.2f}°C.'.format(temperature))
        elif temperature < ( self._setpoint - self._hysteresis ):
            if self.disable():
                self._log.info(Fore.YELLOW + Style.DIM + 'disable fan: cpu temperature: {:5.2f}°C.'.format(temperature))

    # ..........................................................................
    @property
    def enabled(self):
        return self._enabled

    # ..........................................................................
    def enable(self):
        '''
        Enables the fan, returning True if calling the function
        resulted in a change in state.
        '''
        if self._enabled:
            self._log.debug('already enabled.')
            return False
        else:
            self._switch.switch.on()
            self._switch.led.on()
            self._enabled = True 
            self._log.info('enabled.')
            return True

    # ..........................................................................
    def disable(self):
        '''
        Disables the fan, returning True if calling the function
        resulted in a change in state.
        '''
        if self._enabled:
            self._switch.switch.off()
            self._switch.led.off()
            self._enabled = False 
            self._log.info('disabled.')
            return True
        else:
            self._log.debug('already disabled.')
            return False

#EOF
