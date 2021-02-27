#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# Copyright 2020 by Murray Altheim. All rights reserved. This file is part of
# the Robot OS project and is released under the "Apache Licence, Version 2.0".
# Please see the LICENSE file included as part of this package.
#
# author:   Murray Altheim
# created:  2020-09-09
# modified: 2021-02-12
#

import itertools
try:
    from gpiozero import CPUTemperature
    from gpiozero.exc import BadPinFactory
except ModuleNotFoundError:
    print("This script requires the gpiozero module\nInstall with: pip3 install --user gpiozero")
from colorama import init, Fore, Style
init()

from lib.logger import Level, Logger
from lib.feature import Feature
from lib.event import Event
from lib.message import Message
from lib.message_bus import MessageBus

class Temperature(Feature):
    '''
    Obtains the current temperature of the Raspberry Pi CPU. If the value
    exceeds the configured threshold, is_max_temperature() returns True.

    This can be used simply to return values, or tied to a Clock. The
    Clock is optional: if provided a message will be sent to its internal
    MessageBus if the temperature exceeds the set threshold.

    :param config:  the application configuration
    :param clock:   the optional system Clock
    :param fan:     the optional cooling Fan
    :param level:   the log level
    '''
    def __init__(self, config, clock, fan, level):
        self._log = Logger('cpu-temp', level)
        if config is None:
            raise ValueError('null configuration argument.')
        _config = config['ros'].get('temperature')
        self._warning_threshold = _config.get('warning_threshold')
        self._max_threshold = _config.get('max_threshold')
        self._log.info('warning threshold: {:5.2f}°C; maximum threshold: {:5.2f}°C'.format(self._warning_threshold, self._max_threshold))
        self._sample_time_sec = _config.get('sample_time_sec') # how often to divide the 1s TOCK messages
        self._log.info('sampling time: {:d}s'.format(self._sample_time_sec))
        self._clock   = clock # optional
        self._fan     = fan # optional
        self._log.info('starting CPU temperature module.')
        self._cpu     = None
        self._borkd   = False
        self._enabled = False
        self._closed  = False
        self._counter = itertools.count()
        try:
            self._cpu = CPUTemperature(min_temp=0.0, max_temp=100.0, threshold=self._max_threshold) # min/max are defaults
            self._log.info('ready.')
        except BadPinFactory as e:
#       except Exception as e:
            self._borkd = True
            self._log.error('error loading CPU temperature module: {}'.format(e))

    # ..........................................................................
    def name(self):
        return 'Temperature'

    # ..........................................................................
    def get_cpu_temperature(self):
        if self._cpu:
            return self._cpu.temperature
        else:
            return -1.0

    # ..........................................................................
    def is_warning_temperature(self):
        if self._cpu:
            return self._cpu.temperature >= self._warning_threshold
        else:
            return False

    # ..........................................................................
    def is_max_temperature(self):
        if self._cpu:
            return self._cpu.is_active
        else:
            return False

    # ..........................................................................
    def display_temperature(self):
        '''
        Writes a pretty print message to the log.
        '''
        if self._cpu:
            _cpu_temp = self._cpu.temperature
            if self.is_warning_temperature():
                self._log.info('CPU temperature: {:5.2f}°C; '.format(_cpu_temp) + Fore.YELLOW + 'HOT!')
            elif self.is_max_temperature():
                self._log.error('CPU temperature: {:5.2f}°C; '.format(_cpu_temp) + Fore.RED + 'TOO HOT!')
            else:
                self._log.info('CPU temperature: {:5.2f}°C; '.format(_cpu_temp) + Fore.GREEN + 'normal.')

    # ..........................................................................
    def handle(self, message):
        '''
        This receives a TOCK message every 1000ms (i.e., at 1Hz), obtaining
        the CPU temperature.

        Writes a pretty print message to the log. If the temperature exceeds
        the threshold and the message queue has been set, sends a HIGH
        TEMPERATURE message.
        '''
        if self._enabled and ( message.event is Event.CLOCK_TOCK ) \
                and (( next(self._counter) % self._sample_time_sec ) == 0 ):
            if self._fan:
                self._fan.react_to_temperature(self._cpu.temperature)
            self.display_temperature()
            if self.is_max_temperature():
                self._log.warning('CPU HIGH TEMPERATURE!')
                if self._clock:
                    _message = Message(Event.HIGH_TEMPERATURE)
                    self._clock.message_bus.add(_message)
        return message

    # ..........................................................................
    def enable(self):
        if self._borkd:
            self._log.warning('cannot enable: CPU temperature not supported by this system.')
        elif not self._closed:
            self._enabled = True
            if self._clock:
                self._clock.message_bus.add_handler(Message, self.handle)
            self._log.info('enabled.')
        else:
            self._log.warning('cannot enable: already closed.')

    # ..........................................................................
    def disable(self):
        if self._enabled:
            if self._fan:
                self._fan.disable()
            self._enabled = False
            self._log.info('disabled.')
        else:
            self._log.warning('already disabled.')

    # ..........................................................................
    def close(self):
        self.disable()
        if self._fan:
            self._fan.close()
        self._closed = True
        self._log.info('closed.')

#EOF
