#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# Copyright 2020 by Murray Altheim. All rights reserved. This file is part of
# the Robot OS project and is released under the "Apache Licence, Version 2.0".
# Please see the LICENSE file included as part of this package.
#
# author:   Murray Altheim
# created:  2020-09-09
# modified: 2020-09-09
#

import time, threading, itertools
from gpiozero import CPUTemperature
from colorama import init, Fore, Style
init()

from lib.logger import Level, Logger
from lib.feature import Feature
from lib.event import Event
from lib.message import Message
from lib.rate import Rate

class Temperature(Feature):
    '''
        Returns the current temperature of the Raspberry Pi CPU.

        If the value exceeds the configured threshold, is_max_temperature() returns True.

        This can be used simply to return values, or via enable() to run as
        a loop. The MessageQueue is optional: if provided a message will be
        sent if the temperature exceeds the set threshold.
    '''
    def __init__(self, config, queue, level):
        self._log = Logger('cpu-temp', level)
        if config is None:
            raise ValueError('null configuration argument.')
        _config = config['ros'].get('temperature')
        self._warning_threshold = _config.get('warning_threshold')
        self._max_threshold = _config.get('max_threshold')
        self._loop_delay_sec_div_10 = _config.get('loop_delay_sec') / 10
        self._log.info('loop delay: {} sec.'.format(self._loop_delay_sec_div_10))
        
        self._queue = queue
        self._cpu = CPUTemperature(min_temp=0.0, max_temp=100.0, threshold=self._max_threshold) # min/max are defaults
        self._count = 0
        self._counter = itertools.count()
        self._thread  = None
        self._enabled = False
        self._closing = False
        self._closed  = False
        self._log.info('ready.')

    # ..........................................................................
    def name(self):
        return 'Temperature'

    # ..........................................................................
    def get_cpu_temperature(self):
        return self._cpu.temperature

    # ..........................................................................
    def is_warning_temperature(self):
        return self._cpu.temperature >= self._warning_threshold

    # ..........................................................................
    def is_max_temperature(self):
        return self._cpu.is_active

    # ..........................................................................
    def display_temperature(self):
        '''
            Writes a pretty print message to the log.
        '''
        _cpu_temp = self._cpu.temperature
        if self.is_warning_temperature():
            self._log.warning('CPU temperature:\t{:5.2f}°C;'.format(_cpu_temp) + Fore.RED + Style.BRIGHT + '\tHOT!')
        elif self.is_max_temperature():
            self._log.error('CPU temperature:\t{:5.2f}°C;'.format(_cpu_temp) + Style.BRIGHT + '\tTOO HOT!')
        else:
            self._log.info('CPU temperature:\t{:5.2f}°C;'.format(_cpu_temp) + Fore.GREEN + '\tnormal')

    # ..........................................................................
    def _log(self):
        '''
            Writes a pretty print message to the log. If the temperature exceeds
            the threshold and the message queue has been set, sends a HIGH
            TEMPERATURE message.
 
            We actually loop 10x faster than the specified delay but only process
            every tenth loop. This is so that we can exit the loop quickly.
        '''
        while self._enabled:
            self._count = next(self._counter)
            if self._count % 10 == 0:
                self.display_temperature()
                if self.is_max_temperature():
                    if self._queue:
                        self._log.debug('sending HIGH TEMPERATURE message')
                        _message = Message(Event.HIGH_TEMPERATURE)
                        self._queue.add(_message)
            time.sleep(self._loop_delay_sec_div_10)

        self._log.info('exited loop.')

    # ..........................................................................
    def _start_loop(self):
        if not self._enabled:
            raise Exception('attempt to start loop while disabled.')
        elif not self._closed:
            if self._thread is None:
                self._thread = threading.Thread(target=Temperature._log, args=[self])
                self._thread.start()
                self._log.info('started.')
            else:
                self._log.warning('cannot enable: process already running.')
        else:
            self._log.warning('cannot enable: already closed.')

    # ..........................................................................
    def enable(self):
        if not self._enabled:
            if not self._closed:
                self._log.info('enabled temperature.')
                self._enabled = True
                if self._thread is None:
                    self._start_loop()
                else:
                    self._log.error('cannot start: already in loop.')
            else:
                self._log.warning('cannot enable: already closed.')
        else:
            self._log.warning('already enabled.')

    # ..........................................................................
    def disable(self):
        self._log.info('disabled.')
        self._enabled = False

    # ..........................................................................
    def close(self):
        '''
            Permanently close and disable the temperature check.
        '''
        if self._closing:
            self._log.info('already closing temperature check.')
            return
        if not self._closed:
            if self._enabled:
                self.disable()
            self._closing = True
            self._log.info('closing...')
            try:
                self._enabled = False
                if self._thread != None:
                    self._thread.join(timeout=1.0)
                    self._thread = None
                self._closed = True
                self._log.info('closed.')
            except Exception as e:
                self._log.error('error closing: {}'.format(e))
        else:
            self._log.debug('already closed.')



#EOF
