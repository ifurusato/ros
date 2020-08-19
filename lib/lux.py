#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# Copyright 2020 by Murray Altheim. All rights reserved. This file is part of
# the Robot Operating System project and is released under the "Apache Licence, 
# Version 2.0". Please see the LICENSE file included as part of this package.
#
# author:   Murray Altheim
# created:  2020-08-20
# modified: 2020-08-20
#

import time
from ltr559 import LTR559

from lib.logger import Level, Logger

class Lux():
    '''
        Uses the Pimoroni LTR-559 Light and Proximity Sensor to return a lux value.
    '''
    def __init__(self, level):
        self._log = Logger("lux", level)
        self._ltr559 = LTR559()
        self._log.info('ready.')

    def get_value(self):
        self._ltr559.update_sensor()
        _lux = self._ltr559.get_lux()
        self._log.debug("lux: {:06.2f}".format(_lux))
        return _lux

