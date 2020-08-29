#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# Copyright 2020 by Murray Altheim. All rights reserved. This file is part of
# the Robot OS project and is released under the "Apache Licence, Version 2.0".
# Please see the LICENSE file included as part of this package.
#
# author:   Murray Altheim
# created:  2020-08-15
# modified: 2020-08-15
#
#  A simplifying wrapper around a BNO055 used solely as a compass.
#

import time
from threading import Thread
from colorama import init, Fore, Style
init()

from lib.logger import Level, Logger
from lib.enums import Color
from lib.bno055 import BNO055

# ..............................................................................
class Compass():
    '''
        A simplifying wrapper around a BNO055 used as a compass.

        It must be first enabled to function.
    '''
    def __init__(self, config, queue, indicator, level):
        super().__init__()
        if config is None:
            raise ValueError('no configuration provided.')
        self._log = Logger('compass', level)
        self._queue     = queue
        self._indicator = indicator
        self._enabled   = False
        self._thread    = None
        self._bno055 = BNO055(config, queue, Level.INFO)
        _config = config['ros'].get('compass')
        # any config?
        self._log.info('ready.')

    # ..........................................................................
    def get_heading(self):
        return self._bno055.get_heading()

    # ..........................................................................
    def is_calibrated(self):
        return self._bno055.is_calibrated()

    # ..........................................................................
    def enable(self):
        self._enabled = True
        self._bno055.enable()
        if self._indicator:
            self.start_indicator()
        self._log.info('enabled.')

    # ..........................................................................
    def disable(self):
        '''
            Used to halt the Indicator loop.
        '''
        self._enabled = False
        self._log.info('disabled.')

    # ..........................................................................
    def _indicate(self):
        while self._enabled:
            heading = self._bno055.get_heading()
            if heading is None:
                self._log.info(Fore.RED  + Style.NORMAL + '> heading: none')
#               self._indicator.set_color(Color.BLACK)
                self._indicator.set_heading(-1)
            elif self.is_calibrated():
                self._log.info(Fore.MAGENTA + Style.BRIGHT + '> heading: {:5.2f}°'.format(heading))
                self._indicator.set_heading(heading)
            else:
                self._log.info(Fore.CYAN + Style.NORMAL + '> heading: {:5.2f}°'.format(heading))
#               self._indicator.set_color(Color.VERY_DARK_GREY)
                self._indicator.set_heading(-2)
            time.sleep(0.05)

    # ..........................................................................
    def start_indicator(self):
        '''
            If an RGBMatrix5x5 is a available as an Indicator, starts a thread to indicate the current heading.
        '''
        if self._indicator:
            if self._thread == None:
                self._thread = Thread(target=self._indicate, args=())
                self._log.info(Fore.MAGENTA + Style.BRIGHT + 'indicator thread starting...')
                self._thread.start()
                self._log.info(Fore.MAGENTA + Style.BRIGHT + 'indicator thread started.')
#               self._log.info(Fore.MAGENTA + Style.BRIGHT + 'indicator thread started; joining...')
#               self._thread.join()
#               self._log.info(Fore.MAGENTA + Style.BRIGHT + 'indicator thread joined.')
#               self._thread = None
#               self._log.info(Fore.MAGENTA + Style.BRIGHT + 'indicator thread nulled.')
            else:
                self._log.warning('indicator thread already running.')
        else:
            self._log.warning('no indicator available.')

    # ..........................................................................
    def close(self):
        return self._bno055.close()

#EOF
