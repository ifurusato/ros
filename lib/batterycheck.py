#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# Copyright 2020 by Murray Altheim. All rights reserved. This file is part of
# the Robot OS project and is released under the "Apache Licence, Version 2.0".
# Please see the LICENSE file included as part of this package.
#
# author:   Murray Altheim
# created:  2020-03-16
# modified: 2020-03-26
#

import time, threading
from colorama import init, Fore, Style
init()

#from ads1015 import ADS1015
try:
    from ads1015 import ADS1015
    print('import            :' + Fore.BLACK + ' INFO  : successfully imported ads1015.' + Style.RESET_ALL)
except ImportError:
    print('import            :' + Fore.RED + ' ERROR : failed to import ads1015, using mock...' + Style.RESET_ALL)
    from lib.mock_ads1015 import ADS1015

from lib.logger import Level, Logger
from lib.event import Event
from lib.message import Message
from lib.feature import Feature

class BatteryCheck(Feature): 
    '''
        This uses two channels of an ADS1015 to measure both the raw voltage of the 
        battery and that of the 5 volt regulator. If either fall below a specified
        threshold a low battery message is sent to the message queue.

        battery_channel:   the ADS1015 channel: 0, 1 or 2 used to measure the raw battery voltage
        five_volt_channel: the ADS1015 channel: 0, 1 or 2 used to measure the 5v regulator battery voltage
        queue:     the message queue
        level:     the logging level
    '''

    # configuration ....................
    CHANNELS = ['in0/ref', 'in1/ref', 'in2/ref']
    FIVE_VOLT_CHANNEL        = 1
    BATTERY_CHANNEL          = 2
    # how many times should we sample before accepting a first value?
    SETTLE_COUNT             = 3
    # raw and 5v regulator thresholds set from known measurements:
    RAW_BATTERY_THRESHOLD    = 17.74
    LOW_5V_BATTERY_THRESHOLD = 4.75
#   LOW_5V_BATTERY_THRESHOLD = 4.82
    # how long between sampling?

    def __init__(self, config, queue, level):
        self._log = Logger("battery", level)
        self._config = config
        if self._config:
            self._log.info('configuration provided.')
            self._enable_messaging = self._config['ros'].get('battery').get('enable_messaging')
            self._log.info('enable messaging: {}'.format(self._enable_messaging))
        else:
            self._log.warning('no configuration provided.')
            self._enable_messaging = False
            self._log.info('enable messaging: {} (default)'.format(self._enable_messaging))
        # move all this manual config to YAML config
        self._queue = queue
        self._battery_channel       = BatteryCheck.CHANNELS[BatteryCheck.BATTERY_CHANNEL]
        self._five_volt_channel     = BatteryCheck.CHANNELS[BatteryCheck.FIVE_VOLT_CHANNEL]
        self._raw_battery_threshold = BatteryCheck.RAW_BATTERY_THRESHOLD
        self._five_volt_threshold   = BatteryCheck.LOW_5V_BATTERY_THRESHOLD
        self._battery_voltage       = 0.0
        self._regulator_voltage     = 0.0
        self._log.info('setting 5v regulator threshold to {:>5.2f}v on channel {}, raw battery threshold to {:>5.2f}v on channel {}'.format(\
                self._five_volt_threshold, self._five_volt_channel, self._raw_battery_threshold, self._battery_channel))
        self._ads1015 = ADS1015()
        self._ads1015.set_mode('single')
        self._ads1015.set_programmable_gain(2.048)
        self._ads1015.set_sample_rate(1600)
        self._reference = self._ads1015.get_reference_voltage()
        self._log.info('reference voltage: {:6.3f}v'.format(self._reference))
        if level is Level.DEBUG:
            self._loop_delay_sec = 1 # seconds
        else:
            self._loop_delay_sec = 3
        self._is_ready = False
        self._closed = False
        self._thread = None
        self._log.info('ready.')


    # ..........................................................................
    def name(self):
        return 'BatteryCheck'


    # ..........................................................................
    def set_raw_battery_threshold(self, threshold):
        self._log.info('set raw battery threshold to {:>5.2f}v'.format(threshold))
        self._raw_battery_threshold = threshold


    # ..........................................................................
    def set_five_volt_threshold(self, threshold):
        self._log.info('set five volt threshold to {:>5.2f}v'.format(threshold))
        self._five_volt_threshold = threshold


    # ..........................................................................
    def get_raw_battery_voltage(self):
        return self._battery_voltage


    # ..........................................................................
    def get_regulator_voltage(self):
        return self._regulator_voltage


    # ..........................................................................
    def is_ready(self):
        '''
            Returns true after the battery check has ran a few times, which seems
            to stabilise its output. This also may be used as a sanity check.
        '''
        return self._is_ready


    # ..........................................................................
    def _battery_check(self):
        '''
            The function that checks the raw battery and 5v regulator voltages in a loop.
            Note that this doesn't immediately send BATTERY_LOW messages until after the
            loop has run a few times, as it seems the first check after starting tends to
            measure a bit low.
        '''
        self._log.info('battery check started...')
        count = 0
        while self._enabled:
            self._battery_voltage   = self._ads1015.get_compensated_voltage(channel=self._battery_channel, reference_voltage=self._reference)
            self._regulator_voltage = self._ads1015.get_compensated_voltage(channel=self._five_volt_channel, reference_voltage=self._reference)
#               self._log.info(Style.BRIGHT + Fore.CYAN + 'BATTERY: {:>5.2f}v'.format(self._battery_voltage) + Style.RESET_ALL)
#               self._log.info(Style.BRIGHT + Fore.CYAN + '5V REG:  {:>5.2f}v'.format(self._regulator_voltage) + Style.RESET_ALL)
            self._is_ready = count > BatteryCheck.SETTLE_COUNT
            if self._is_ready:
                if self._battery_voltage < self._raw_battery_threshold:
                    self._log.warning('battery low: {:>5.2f}v'.format(self._battery_voltage))
                    if self._enable_messaging:
                        self._queue.add(Message(Event.BATTERY_LOW))
                elif self._regulator_voltage < self._five_volt_threshold:
                    self._log.warning('5V regulator low:  {:>5.2f}v'.format(self._regulator_voltage))
                    if self._enable_messaging:
                        self._queue.add(Message(Event.BATTERY_LOW))
                else:
                    self._log.info(Style.DIM + 'battery: {:>5.2f}v; regulator: {:>5.2f}v'.format(self._battery_voltage, self._regulator_voltage))
            else:
                self._log.debug('battery: {:>5.2f}v; regulator: {:>5.2f}v (stabilising)'.format(self._battery_voltage, self._regulator_voltage))
            time.sleep(self._loop_delay_sec)
            count += 1

        self._log.info('battery check ended.')


    # ..........................................................................
    def enable(self):
        if not self._closed:
            self._enabled = True
            # if we haven't started the thread yet, do so now...
            if self._thread is None:
                self._thread = threading.Thread(target=BatteryCheck._battery_check, args=[self])
                self._thread.start()
                self._log.info('enabled.')
            else:
                self._log.warning('cannot enable: thread already exists.')
        else:
            self._log.warning('cannot enable: already closed.')


    # ..........................................................................
    def disable(self):
        self._enabled = False
        if self._thread is not None:
            self._thread.join(timeout=self._loop_delay_sec)
            self._log.debug('battery check thread joined.')
            self._thread = None
        self._log.info('disabled.')


    # ..........................................................................
    def close(self):
        self.disable()
        self._closed = True
        self._log.info('closed.')


    # ..........................................................................
    @staticmethod
    def clamp(n, minn, maxn):
        return max(min(maxn, n), minn)
 

    # ..........................................................................
    @staticmethod
    def remap(x, in_min, in_max, out_min, out_max):
        return (x - in_min) * (out_max - out_min) / (in_max - in_min) + out_min


#EOF
