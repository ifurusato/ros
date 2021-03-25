#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# Copyright 2020-2021 by Murray Altheim. All rights reserved. This file is part
# of the Robot Operating System project, released under the MIT License. Please
# see the LICENSE file included as part of this package.
#
# author:   Murray Altheim
# created:  2020-03-16
# modified: 2021-03-25
#

import sys, traceback
from colorama import init, Fore, Style
init()

try:
    from ads1015 import ADS1015
except ImportError:
    sys.exit("This script requires the ads1015 module\nInstall with: pip3 install --user ads1015")

from lib.logger import Level, Logger

class AnalogInput(object): 
    '''
    This is a highly simplified version of the lib.batterycheck.py class, using a
    Pimoroni ADS1015 to measure both the voltage of its 3 input pins and display
    the results when called upon. There are getter methods to obtain the latest
    readings. Nothing fancy, no events, no messaging.

    If unable to establish communication with the ADS1015 this will raise a
    RuntimeError.
    '''
    def __init__(self, level):
        self._log = Logger("ads1015", level)
        self._channel_0_voltage = 0.0
        self._channel_1_voltage = 0.0
        self._channel_2_voltage = 0.0
        try:
            self._ads1015 = ADS1015()
            self._ads1015.set_mode('single')
            self._ads1015.set_programmable_gain(2.048)
            self._ads1015.set_sample_rate(1600)
            self._reference = self._ads1015.get_reference_voltage()
            self._log.info('reference voltage: {:6.3f}v'.format(self._reference))
        except Exception as e:
            raise RuntimeError('error configuring AD converter: {}'.format(traceback.format_exc()))
        self._log.info('ready.')

    # ..........................................................................
    @property
    def name(self):
        return 'BatteryCheck'

    # ..........................................................................
    def get_channel_0_voltage(self):
        return self._channel_0_voltage

    # ..........................................................................
    def get_channel_1_voltage(self):
        return self._channel_1_voltage

    # ..........................................................................
    def get_channel_2_voltage(self):
        return self._channel_2_voltage

    # ..........................................................................
    def read(self):
        '''
        This reads the three channels, populates their respective variables,
        prints a report to the log, then returns a tuple of the three.
        '''
        self._channel_0_voltage = self._ads1015.get_compensated_voltage(channel='in0/ref', reference_voltage=self._reference)
        self._channel_1_voltage = self._ads1015.get_compensated_voltage(channel='in1/ref', reference_voltage=self._reference)
        self._channel_2_voltage = self._ads1015.get_compensated_voltage(channel='in2/ref', reference_voltage=self._reference)
        self._log.info(Style.DIM + 'channel 0: {:5.2f}V; channel 1: {:5.2f}V; channel 2: {:5.2f}V.'.format(\
                self._channel_0_voltage, self._channel_1_voltage, self._channel_2_voltage))
        self._log.info(Style.DIM + 'analog read complete.')
        return [ self._channel_0_voltage, self._channel_1_voltage, self._channel_2_voltage ]

#EOF
