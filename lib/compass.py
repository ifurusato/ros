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
from lib.bno055_v3 import Calibration, BNO055

# ..............................................................................
class Compass():
    '''
        A simplifying wrapper around a BNO055 used as a compass. This reads
        the heading and ignores pitch and roll, assuming the robot is on 
        flat ground.

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
        self._has_been_calibrated = False
        # any config?
        self._log.info('ready.')

    # ..........................................................................
    def enable(self):
        self._enabled = True
        self._bno055.enable()
        if self._indicator:
            self.start_indicator()
        self._log.info('enabled.')

    # ..........................................................................
    def get_heading(self):
        '''
            Returns a tuple containing a Calibration enum indicating the state
            of the sensor calibration followed by the heading value. If the 
            result ever indicates the sensor is calibrated, this sets a flag.
        '''
        _tuple = self._bno055.get_heading()
        _calibration = _tuple[0]
        if _calibration.calibrated:
            self._has_been_calibrated = True
        return _tuple

    # ..........................................................................
    def _indicate(self):
        '''
            The thread method that reads the heading from the BNO055 and 
            sends the value to the Indicator for display.
        '''
        while self._enabled:
            _result = self.get_heading()
            _calibration = _result[0]
            _heading = _result[1]

            if _calibration is Calibration.NEVER:
                self._log.info(Fore.BLACK + Style.NORMAL   + 'heading: {:5.2f}° (never);'.format(_heading))
                self._indicator.set_heading(-1)

            elif _calibration is Calibration.LOST:
                self._log.info(Fore.CYAN + Style.NORMAL    + 'heading: {:5.2f}° (lost);'.format(_heading))
                self._indicator.set_heading(_heading) # last value read

            elif _calibration is Calibration.CALIBRATED:
                self._log.info(Fore.MAGENTA + Style.NORMAL + 'heading: {:5.2f}° (calibrated);'.format(_heading))
                self._indicator.set_heading(_heading)

            elif _calibration is Calibration.TRUSTED:
                self._log.info(Fore.MAGENTA + Style.BRIGHT + 'heading: {:5.2f}° (trusted);'.format(_heading))
                self._indicator.set_heading(_heading)

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
    def disable(self):
        '''
            Used to halt the Indicator loop.
        '''
        self._bno055.disable()
        self._enabled = False
        self._log.info('disabled.')

    # ..........................................................................
    def close(self):
        if self._enabled:
            self.disable()
        self._bno055.close()
        self._log.info('closed.')


#EOF
