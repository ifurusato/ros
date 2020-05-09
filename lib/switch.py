#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# Copyright 2020 by Murray Altheim. All rights reserved. This file is part of
# the Robot OS project and is released under the "Apache Licence, Version 2.0".
# Please see the LICENSE file included as part of this package.
#
# author:   Murray Altheim
# created:  2020-01-18
# modified: 2020-03-26
#

import time
from colorama import init, Fore, Style
init()

from .logger import Logger, Level

from ht0740 import HT0740
try:
    from ht0740 import HT0740
    print('import            :' + Fore.BLACK + ' INFO  : successfully imported HT0740.' + Style.RESET_ALL)
except ImportError:
    print('import            :' + Fore.RED + ' ERROR : failed to import HT0740, using mock...' + Style.RESET_ALL)
    from .mock_ht0740 import MockHT0740 as HT0740


class Switch():
    '''
        Uses the HT0740 Switch to control power to a subset of the sensors, so
        that the robot can "power-down" when batteries are critically low.
    '''
    def __init__(self, level):
        super().__init__()
        self._log = Logger("switch", level)
        self._log.debug('initialising and enabling switch...')
        self._switch = HT0740()
        self._switch.enable()
        self._log.info('ready.')


    def enable(self):
        self._log.info("enable switch.")
        self._switch.enable()


    def on(self):
        self._log.info("turn switch on.")
        self._switch.switch.on()
        self._switch.led.on()


    def off(self):
        self._log.info("turn switch off.")
        self._switch.switch.off()
        self._switch.led.off()


    def disable(self):
        self._log.info("disable switch.")
        self._switch.disable()


    def close(self):
        self._log.debug("closing switch.")
        self._switch.switch.off()
        self._switch.led.off()
        self._switch.disable()
        self._log.info("closed switch.")


#EOF
