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

class Fan(object):
    '''
    Uses an HT0740 switch to turn a cooling fan on or off.
    '''
    def __init__(self, config, level):
        self._log = Logger("fan", level)
        if config is None:
            raise ValueError('no configuration provided.')
        _config = config['ros'].get('fan')
        _i2c_address = _config.get('i2c_address')
        self._switch = HT0740(i2c_addr=0x39)
        self._log.info("enabling fan.")
        self._switch.enable()
        self._enabled = False 
        self._log.info('ready.')

    # ..........................................................................
    @property
    def enabled(self):
        return self._enabled

    # ..........................................................................
    def enable(self):
        if self._enabled:
            self._log.debug('already enabled.')
        else:
            self._switch.switch.on()
            self._switch.led.on()
            self._enabled = True 
            self._log.info('enabled.')

    # ..........................................................................
    def disable(self):
        if self._enabled:
            self._switch.switch.off()
            self._switch.led.off()
            self._enabled = False 
            self._log.info('disabled.')
        else:
            self._log.debug('already disabled.')

#EOF
