#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# Copyright 2020 by Murray Altheim. All rights reserved. This file is part of
# the Robot OS project and is released under the "Apache Licence, Version 2.0".
# Please see the LICENSE file included as part of this package.
#
# author:  Murray Altheim
# created: 2020-03-16

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


CHANNELS = ['in0/ref', 'in1/ref', 'in2/ref']

class LongRangeInfrared:
    '''
        This does a rough conversion from voltage to distance in cm, "rough" in the
        sense that the centimeter value returned is only approximate.

        This sets two thresholds:
        a short and a long range. Note that both are not triggered as messages: if the short
        range threshold is met, it is sent in lieu of the long range message.

        channel:   the ADS1015 channel: 0, 1 or 2
        queue:     the message queue
        level:     the logging level
    '''
    def __init__(self, queue, channel, level):
        self._log = Logger("lrir", level)
        self._channel = CHANNELS[channel]
        self._queue = queue
        self._short_range_threshold_value_cm = 40.0
        self._long_range_threshold_value_cm  = 52.0
        self._log.info('setting short range infrared sensor to {:>5.1f}cm, long range to {:>5.1f}cm'.format(self._short_range_threshold_value_cm, self._long_range_threshold_value_cm))
        self._ads1015 = ADS1015()
        self._ads1015.set_mode('single')
        self._ads1015.set_programmable_gain(2.048)
        self._ads1015.set_sample_rate(1600)
        self._reference = self._ads1015.get_reference_voltage()
        self._log.info('reference voltage: {:6.3f}v'.format(self._reference))
        self._enable_long_range_scan = True
        self._short_range_hits = 0
        self._long_range_hits  = 0
        self._closed = False
        self._thread = None
        self._log.info('ready.')


    def set_long_range_scan(self, enabled):
        '''
            Enable or disable the long range scan. Disabling it is necessary
            in order to continue past the long range threshold.
        '''
        self._log.info('setting long-range infrared scanning to {}.'.format(enabled))
        self._enable_long_range_scan = enabled


    def get_short_range_hits(self):
        '''
            Returns the number of short range hits on the sensor.
            This counter is cleared continuously.
        '''
        return self._short_range_hits


    def get_long_range_hits(self):
        '''
            Returns the number of long range hits on the sensor.
            This counter is cleared continuously.
        '''
        return self._long_range_hits



    # ..........................................................................
    def _scan_infrared(self):
        self._log.info('starting long-range infrared scanning...')
        # alive loop
#       FUDGE_FACTOR = 0.85
        FUDGE_FACTOR = 0.80
#       FUDGE_FACTOR = 0.75

        count = 0
        settle_count = 8
        bucket_count = 7
        short_range_threshold = 5
        long_range_threshold  = 5
        delay_sec = 0.05

        while not self._closed:

            if self._enabled:

                # BEGIN settle loop ..................................

                value = self._ads1015.get_compensated_voltage(channel=self._channel, reference_voltage=self._reference)
                self._log.debug(Style.BRIGHT + Fore.YELLOW + 'VALUE : {:>5.2f}v'.format(value))
                limited_value = self.clamp(value, 0.1, 3.2)
                distance = self.remap( limited_value, 0.1, 3.2, 80.0, 10.0 ) * FUDGE_FACTOR
                if count > settle_count:

                    if distance < self._short_range_threshold_value_cm:
                        self._short_range_hits += 1
                        if self._short_range_hits > short_range_threshold:
                            self._log.info(Style.BRIGHT + Fore.YELLOW + 'SHORT RANGE HIT: A0 value: {:>5.2f}v/{:>5.2f}v;'.format(value, limited_value) \
                                + Fore.RED + ' distance: {:7.3} cm'.format(distance) + Style.RESET_ALL)
                            self._queue.add(Message(Event.INFRARED_SHORT_RANGE))
                            self._short_range_hits = 0
                        else:
                            self._log.debug(Style.DIM + Fore.MAGENTA + 'DID NOT MEET THRESHOLD ({:d}/{:d}); SHORT RANGE: A0 value: {:>5.2f}v/{:>5.2f}v;'.format(\
                                    self._short_range_hits, short_range_threshold, value, limited_value) \
                                + Fore.RED + ' distance: {:7.3} cm'.format(distance) + Style.RESET_ALL)

                    elif self._enable_long_range_scan and distance < self._long_range_threshold_value_cm:
                        self._long_range_hits += 1
                        if self._long_range_hits > long_range_threshold:
                            self._log.info(Style.BRIGHT + Fore.MAGENTA + 'LONG RANGE HIT: A0 value: {:>5.2f}v/{:>5.2f}v;'.format(value, limited_value) \
                                + Fore.RED + ' distance: {:7.3} cm'.format(distance) + Style.RESET_ALL)
                            self._queue.add(Message(Event.INFRARED_LONG_RANGE))
                            self._long_range_hits = 0
                        else:
                            self._log.debug(Style.DIM + Fore.MAGENTA + 'DID NOT MEET THRESHOLD ({:d}/{:d}); LONG RANGE: A0 value: {:>5.2f}v/{:>5.2f}v;'.format(\
                                    self._long_range_hits, short_range_threshold, value, limited_value) \
                                + Fore.RED + ' distance: {:7.3} cm'.format(distance) + Style.RESET_ALL)
                    else:
                        self._log.debug(Fore.MAGENTA + 'A0 value: {:>5.2f}v/{:>5.2f}v;'.format(value, limited_value) + Fore.GREEN + ' distance: {:7.3} cm'.format(distance) + Style.RESET_ALL)

                else:
                    # still settling down...
                    self._log.debug(Style.DIM + Fore.MAGENTA + 'A0 value: {:>5.2f}v/{:>5.2f}v;'.format(value, limited_value) \
                        + Fore.GREEN + ' distance: {:7.3} cm (settling)'.format(distance) + Style.RESET_ALL)

                if count % bucket_count == 0: # then clear counts
                    self._short_range_hits = 0
                    self._long_range_hits = 0
                    self._log.debug(Fore.MAGENTA + 'cleared buckets.' + Style.RESET_ALL)

                time.sleep(delay_sec)
                # END settle loop ....................................

            else:
                self._log.debug('disabled loop.')
                time.sleep(1)

            count += 1

            # end of while loop ......................................

        self._log.info('long-range infrared scanning thread ended.')

    # ..........................................................................
    def enable(self):
        if self._closed:
            self._log.warning('cannot enable: already closed.')
        else:
            self._enabled = True
            self.set_long_range_scan(True)
            # if we haven't started the thread yet, do so now...
            if self._thread is None:
                self._thread = threading.Thread(target=LongRangeInfrared._scan_infrared, args=[self])
                self._thread.start()
            self._log.info('enabled.')


    # ..........................................................................
    def disable(self):
        self._enabled = False
        self._log.info('disabled.')


    # ..........................................................................
    def close(self):
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
