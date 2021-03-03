#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# Copyright 2020-2021 by Murray Altheim. All rights reserved. This file is part
# of the Robot Operating System project, released under the MIT License. Please
# see the LICENSE file included as part of this package.
#
# author:   Murray Altheim
# created:  2021-03-02
# modified: 2021-03-03
#

import sys, itertools, traceback, os.path
from collections import deque as Deque
from os import path
from datetime import datetime as dt
import statistics
from colorama import init, Fore, Style
init()
try:
    from gpiozero import DigitalInputDevice
except Exception:
    print('unable to import gpiozero.')

from lib.logger import Level, Logger

# ..............................................................................

# Raspberry Pi file paths
HWCLOCK_BOOTCONFIG_PATH = '/boot/config.txt'
HWCLOCK_EXPORT_PATH     = '/sys/class/pwm/pwmchip0/export'
HWCLOCK_PWM1_PATH       = '/sys/class/pwm/pwmchip0/pwm1'
HWCLOCK_PERIOD_PATH     = '/sys/class/pwm/pwmchip0/pwm1/period'
HWCLOCK_DUTY_CYCLE_PATH = '/sys/class/pwm/pwmchip0/pwm1/duty_cycle'
HWCLOCK_ENABLE_PATH     = '/sys/class/pwm/pwmchip0/pwm1/enable'

class HardwareClock(object):
    '''
    A hardware clock based on using one of the Raspberry Pi's hardware
    clocks as a 20Hz system clock. In order to enable hardware-based
    pulse-width modulation (PWM):

      * Edit /boot/config.txt.
      * Add the line dtoverlay=pwm-2chan
      * Save the file.
      * Reboot.

    This automagically creates a new directory at:

      /sys/class/pwm/pwmchip0

    containing a bunch of files. If you write a "1" to the 'export' file,
    this will create a new directory:

      /sys/class/pwm/pwmchip0/pwm1/

    which will contain a number of configuration files, generally each
    containing a single line containing a single value.

    For a 20Hz system clock the period is 50ms, which must be written to
    the 'period' configuration file as a value in nanoseconds. Likewise,
    the 50% duty cycle is expressed as half of the period and written to
    the 'duty_cycle' file. Then a "1" (True) is written to the 'enable'
    file to start the timer. This is shown below:

      echo 50000000 > /sys/class/pwm/pwmchip0/pwm1/period
      echo 25000000 > /sys/class/pwm/pwmchip0/pwm1/duty_cycle
      echo 1 > /sys/class/pwm/pwmchip0/pwm1/enable

    And that's it. You can connect an LED between BCM pin 19 and ground
    through an appropriate resistor and you'll see it vibrating away at
    20Hz.
    '''
    def __init__(self, level):
        self._log = Logger("hwclock", level)
        self._check_boot_config()
        self._configure()
        self._callbacks = []
        _pin = 21 # BCM 21
        self._sensor = DigitalInputDevice(_pin, pull_up=False)
        self._sensor.when_activated   = self._activated
#       self._sensor.when_deactivated = self._deactivated
        self._enabled = False
        # testing ....................
        self._dt_ms = 50.0 # loop delay in milliseconds 
        self._queue_len = 50 # larger number means it takes longer to change
        self._queue  = Deque([], maxlen=self._queue_len)
        self._counter = itertools.count()
        self._last_time = dt.now()
        self._max_error = 0.0
        self._max_vari  = 0.0
        self._log.info('ready.')

    # ..........................................................................
    def _get_mean(self, value):
        '''
        Returns the mean of measured values.
        '''
        self._queue.append(value)
        _n = 0
        _mean = 0.0
        for x in self._queue:
            _n += 1
            _mean += ( x - _mean ) / _n
        if _n < 1:
            return float('nan');
        else:
            return _mean

    # ..........................................................................
    def add_callback(self, callback):
        self._callbacks.append(callback)

    # ..........................................................................
    def _activated(self):
        '''
        The default function called when the sensor is activated.
        '''
        if self._enabled:
            for callback in self._callbacks:
                callback()
        else:
            self._log.info('hardware clock disabled.')

    # ..........................................................................
    def _deactivated(self):
        '''
        The default function called when the sensor is deactivated.
        '''
        if self._enabled:
            self._log.info('tick off!')
        else:
            self._log.info('hardware clock disabled.')

    # ..........................................................................
    def set_messaging(self, message_bus, message_factory):
        self._message_factory = message_factory

    # ..........................................................................
    def _check_boot_config(self):
        _term = 'dtoverlay=pwm-2chan'
        with open(HWCLOCK_BOOTCONFIG_PATH,) as f:
            lines = [line.rstrip() for line in f]
            for line in lines:
                if line.startswith(_term):
                    self._log.info(Fore.CYAN + 'PWM support found in boot configuration.' + Style.RESET_ALL)
                    return
        sys.exit(Fore.RED + '''
For a hardware clock, PWM support needs to be added to the boot configuration:

  * Edit the file: /boot/config.txt
  * Add the line:  dtoverlay=pwm-2chan
  * Save the file.
  * Reboot.
''' + Style.RESET_ALL)

    # ..........................................................................
    def _configure(self):
        # static logger specific to configure()
        if not path.exists(HWCLOCK_PWM1_PATH):
            if os.geteuid() != 0:
                sys.exit(Fore.RED + 'You need to have root privileges to run this script.\nPlease try again, this time using \'sudo\'. Exiting.' + Style.RESET_ALL)
            self._log.info(Fore.CYAN + 'no hardware clock configured; configuring...' + Style.RESET_ALL)
            HardwareClock._write_to_file(HWCLOCK_EXPORT_PATH, '1')
            if path.exists(HWCLOCK_PWM1_PATH):
                self._log.info(Fore.CYAN + 'created PWM configuration files at: {}'.format(HWCLOCK_PWM1_PATH) + Style.RESET_ALL)
            else:
                raise Exception('cannot continue: expected creation of pwm1 directory.')
                sys.exit(1)
        else:
            self._log.info('hardware clock already configured.' + Style.RESET_ALL)
        self._log.info('found existing PWM configuration files at: {}'.format(HWCLOCK_PWM1_PATH) + Style.RESET_ALL)
        # now continue: we'll overwrite existing values since it doesn't hurt.
        #
        # For a 20Hz system clock the period is 50ms, but must be written to the
        # configuration file in nanoseconds. Likewise, the 50% duty cycle is
        # expressed as half of the period and written to a separate file. Finally,
        # a "1" is written to the 'enable' file to start the timer:
        #
        # echo 50000000 > /sys/class/pwm/pwmchip0/pwm1/period
        HardwareClock._write_to_file(HWCLOCK_PERIOD_PATH, '50000000')
        # echo 25000000 > /sys/class/pwm/pwmchip0/pwm1/duty_cycle
        HardwareClock._write_to_file(HWCLOCK_DUTY_CYCLE_PATH, '25000000')
        # echo 1 > /sys/class/pwm/pwmchip0/pwm1/enable
        if self.enabled:
            self._log.info(Fore.CYAN + 'currently enabled.')
        else:
            self._log.info(Fore.CYAN + 'currently disabled; enabling...')
            self.enable()
        self._log.info(Fore.CYAN + 'configuration complete: enabled hardware clock: {}'.format(HWCLOCK_ENABLE_PATH) + Style.RESET_ALL)

    # ..........................................................................
    @staticmethod
    def _write_to_file(path, data):
        f = open(path, "w")
        f.write(data)
        f.close()

    # ..........................................................................
    def add_test_callback(self):
        '''
        Adds a callback function used for testing.
        '''
        self.add_callback(self.test_callback_method)

    # ..........................................................................
    def test_callback_method(self):
        if self._enabled:
            _now = dt.now()
            self._count = next(self._counter)
            _delta_ms = 1000.0 * (_now - self._last_time).total_seconds()
            _mean = self._get_mean(_delta_ms)
            if len(self._queue) > 5:
                _error_ms = _delta_ms - self._dt_ms
                self._max_error = max(self._max_error, _error_ms)
                _vari1 = statistics.variance(self._queue) # if len(self._queue) > 5 else 0.0
                _vari  = sum((item - _mean)**2 for item in self._queue) / (len(self._queue) - 1)
                self._max_vari = max(self._max_vari, _vari)
                if self._count <= self._queue_len:
                    _vari = 0.0
                    self._max_vari = 0.0
                else:
                    self._max_vari = max(self._max_vari, _vari)
                if _error_ms > 0.5000:
                    self._log.info(Fore.RED + Style.BRIGHT + '[{:05d}]\tΔ {:8.5f}; err: {:8.5f}; '.format(self._count, _delta_ms, _error_ms) 
                            + Fore.CYAN + Style.NORMAL + 'max err: {:8.5f}; mean: {:8.5f}; max vari: {:8.5f}'.format(self._max_error, _mean, self._max_vari))
                elif _error_ms > 0.1000:
                    self._log.info(Fore.YELLOW + Style.BRIGHT + '[{:05d}]\tΔ {:8.5f}; err: {:8.5f}; '.format(self._count, _delta_ms, _error_ms)
                            + Fore.CYAN + Style.NORMAL + 'max err: {:8.5f}; mean: {:8.5f}; max vari: {:8.5f}'.format(self._max_error, _mean, self._max_vari))
                else:
                    self._log.info(Fore.GREEN  + '[{:05d}]\tΔ {:8.5f}; err: {:8.5f}; '.format(self._count, _delta_ms, _error_ms)
                            + Fore.CYAN                + 'max err: {:8.5f}; mean: {:8.5f}; max vari: {:8.5f}'.format(self._max_error, _mean, self._max_vari))
            else:
                self._log.info(Fore.CYAN + '[{:05d}]\tΔ {:8.5f}; '.format(self._count, _delta_ms) + Fore.CYAN + 'mean: {:8.5f}'.format(_mean))
            self._last_time = _now
            if self._count > 1000: 
                self._log.info('reached count limit, exiting...')
                self.disable()
#               sys.exit(0)

    # ..........................................................................
    @property
    def enabled(self):
        if not path.exists(HWCLOCK_ENABLE_PATH):
            raise Exception('hardware clock enable file \'{}\' not found.'.format(HWCLOCK_ENABLE_PATH))
        f = open(HWCLOCK_ENABLE_PATH, "r")
        line = f.readline().strip()
#       self._log.info(Fore.GREEN + 'line: "{}"'.format(line) + Style.RESET_ALL)
        return line == '1'

    # ..........................................................................
    def enable(self):
        if not path.exists(HWCLOCK_ENABLE_PATH):
            raise Exception('hardware clock enable file \'{}\' not found.'.format(HWCLOCK_ENABLE_PATH))
        self._enabled = True
        HardwareClock._write_to_file(HWCLOCK_ENABLE_PATH, '1')
        self._log.info('enabled.')

    # ..........................................................................
    def disable(self):
        self._callbacks = []
        if not path.exists(HWCLOCK_ENABLE_PATH):
            raise Exception('hardware clock enable file \'{}\' not found.'.format(HWCLOCK_ENABLE_PATH))
        HardwareClock._write_to_file(HWCLOCK_ENABLE_PATH, '0')
        self._enabled = False
        self._log.info('disabled.')

    # ..........................................................................
    def close(self):
        self.disable()

#EOF
