#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# Copyright 2020 by Murray Altheim. All rights reserved. This file is part of
# the Robot Operating System project and is released under the "Apache Licence,
# Version 2.0". Please see the LICENSE file included as part of this package.
#
# author:   Murray Altheim
# created:  2020-05-19
# modified: 2020-11-06
#
# A system clock that ticks and tocks.
#

import sys, time, itertools
from datetime import datetime as dt
from threading import Thread
from colorama import init, Fore, Style
init()

from lib.message import Message
from lib.logger import Logger, Level
from lib.pid import PID
from lib.event import Event
from lib.rate import Rate
#from lib.ioe_pot import Potentiometer

SCALE_KP = True # else scale KD

# ...............................................................
class MockPotentiometer(object):
    '''
    For testing, or when we don't have an RGB LED Potentiometer attached.
    '''
    def __init__(self):
        self._min_pot = 0.0
        self._max_pot = 0.0
        self._value   = 0.0
        self._step    = 0.0

    def set_output_limits(self, min_pot, max_pot):
        self._min_pot = min_pot
        self._max_pot = max_pot
        self._step    = max_pot / 20.0

    def get_scaled_value(self, update_led=True):
        if self._value < self._max_pot:
            self._value += self._step
        else:
            self._value = self._min_pot
        return self._value

# ...............................................................
class Clock(object):
    '''
    A system clock that creates a "TICK" message every loop, alternating with a
    "TOCK" message every modulo-nth loop. Note that the TOCK message replaces the
    TICK, i.e., every nth loop there is no TICK, only a TOCK.

    This passes its messages on to any added consumers, then on to the message bus.
    '''
    def __init__(self, config, message_bus, message_factory, level):
        super().__init__()
        self._message_bus = message_bus
        self._message_factory = message_factory
        self._log = Logger("clock", level)
        if config is None:
            raise ValueError('null configuration argument.')
        _config            = config['ros'].get('clock')
        self._loop_freq_hz = _config.get('loop_freq_hz')
        self._tock_modulo  = _config.get('tock_modulo')
        self._log.info('tock modulo: {:d}'.format(self._tock_modulo))
        self._counter      = itertools.count()
        self._rate         = Rate(self._loop_freq_hz)
        self._tick_type    = type(Tick(None, Event.CLOCK_TICK, None))
        self._tock_type    = type(Tock(None, Event.CLOCK_TOCK, None))
        self._log.info('tick frequency: {:d}Hz'.format(self._loop_freq_hz))
        self._log.info('tock frequency: {:d}Hz'.format(round(self._loop_freq_hz / self._tock_modulo)))
        self._enable_trim  = _config.get('enable_trim')
        if self._enable_trim:
            _min_pot = 0.3
            _max_pot = 0.9
#           self._pot = Potentiometer(config, Level.WARN)
            self._pot = MockPotentiometer()
            self._pot.set_output_limits(_min_pot, _max_pot)

            _kp = 0.0
            _ki = 0.0
            _kd = 0.0
            _setpoint = self._rate.get_period_ms()
            self._log.info(Style.BRIGHT + 'initial PID setpoint: {:6.3f}'.format(_setpoint))
            _min_output = None
            _max_output = None
            _sample_time = 0.05
            self._pid = PID('clock', _kp, _ki, _kd, _min_output, _max_output, _setpoint, _sample_time, Level.WARN)
            self._log.info(Style.BRIGHT + 'trim enabled.')
        else:
            self._pid = None
            self._pot = None
            self._log.info(Style.DIM + 'trim disabled.')
        # .........................
        self._thread       = None
        self._enabled      = False
        self._closed       = False
        self._last_time    = dt.now()
        self._log.info('ready.')

    # ..........................................................................
    @property
    def message_bus(self):
        return self._message_bus

    # ..........................................................................
    @property
    def freq_hz(self):
        return self._loop_freq_hz

    # ..........................................................................
    @property
    def trim(self):
        '''
        Returns the loop trim value. The value is returned from the
        internal Rate object. Default is zero.
        '''
        return self._rate.trim

    # ..........................................................................
    @property
    def dt_ms(self):
        '''
        Returns the time loop delay in milliseconds.
        The value is returned from Rate.
        '''
        return self._rate.dt_ms

    # ..........................................................................
    def _loop(self, f_is_enabled):
        '''
        The clock loop, which executes while the f_is_enabled flag is True. If 
        the trim function is enabled a Proportional control is used to draw the
        clock period towards its set point.
        '''
        while f_is_enabled():
            _now = dt.now()
            _count = next(self._counter)
            if (( _count % self._tock_modulo ) == 0 ):
                _message = self._message_factory.get_message_of_type(self._tock_type, Event.CLOCK_TOCK, _count)
            else:
                _message = self._message_factory.get_message_of_type(self._tick_type, Event.CLOCK_TICK, _count)
            self._message_bus.add(_message)

            if self._pot:
                if SCALE_KP:
                    _scaled_value = self._pot.get_scaled_value(True)
                    self._pid.kp = _scaled_value
#                   self._log.info(Fore.GREEN  + 'scaled value kp: {:8.5f}'.format(_scaled_value))
                else:
                    _scaled_value = self._pot.get_scaled_value(True) / 10.0
                    self._pid.kd = _scaled_value
#                   self._log.info(Fore.GREEN  + 'scaled value kd: {:8.5f}'.format(_scaled_value))

            _kp = 0.0
            _kd = 0.0
            _pid_output = 0.0

            _delta_s = (_now - self._last_time).total_seconds()
            _delta_ms = _delta_s * 1000.0
#           _error_s = (self.dt_ms / 1000.0) - _delta_s
            _error_s = _delta_s - (self.dt_ms / 1000.0)
            _error_ms = _error_s * 1000.0

            if self._enable_trim:
                _pid_output = self._pid(_delta_ms)
                _trim = self._rate.trim
                self._rate.trim = _trim + ( _pid_output / 1000.0 )
#               self._rate.trim = ( _pid_output / 1000.0 )
                _kp = self._pid.kp
                _kd = self._pid.kd

            # display stats
#           if _delta_ms > -50.050 and _delta_ms < 50.050:
            if ( _error_ms ) < 0.110:
                self._log.info(Fore.GREEN  + 'dt: {:8.5f}ms; delta {:8.5f}ms; error: {:8.5f}ms; '.format(self.dt_ms, _delta_ms, _error_ms) \
                        + Fore.BLUE + ' kp: {:7.4f}; kd: {:7.4f}; '.format(_kp, _kd) \
                        + Fore.RED + ' out: {:9.6f}'.format(_pid_output) \
                        + Fore.YELLOW + ' trim: {:9.6f}'.format(self._rate.trim))
            elif ( _error_ms ) > 1.5:
                self._log.info(Fore.RED    + 'dt: {:8.5f}ms; delta {:8.5f}ms; error: {:8.5f}ms; '.format(self.dt_ms, _delta_ms, _error_ms) \
                        + Fore.BLUE + ' kp: {:7.4f}; kd: {:7.4f}; '.format(_kp, _kd) \
                        + Fore.RED + ' out: {:9.6f}'.format(_pid_output) \
                        + Fore.YELLOW + ' trim: {:9.6f}'.format(self._rate.trim))
            else:
                self._log.info(Fore.YELLOW + Style.DIM + 'dt: {:8.5f}ms; delta {:8.5f}ms; error: {:8.5f}ms; '.format(self.dt_ms, _delta_ms, _error_ms) \
                        + Fore.BLUE + Style.NORMAL + ' kp: {:7.4f}; kd: {:7.4f}; '.format(_kp, _kd) \
                        + Fore.RED + ' out: {:9.6f}'.format(_pid_output) \
                        + Fore.YELLOW + ' trim: {:9.6f}'.format(self._rate.trim))

            self._last_time = _now
            self._rate.wait()

        self._log.info('exited clock loop.')

    # ..........................................................................
    @property
    def enabled(self):
        return self._enabled

    # ..........................................................................
    def enable(self):
        if not self._closed:
            if self._enabled:
                self._log.warning('clock already enabled.')
            else:
                # if we haven't started the thread yet, do so now...
                if self._thread is None:
                    self._enabled = True
                    self._thread = Thread(name='clock', target=Clock._loop, args=[self, lambda: self.enabled], daemon=True)
                    self._thread.start()
                    self._log.info('clock enabled.')
                else:
                    self._log.warning('cannot enable clock: thread already exists.')
        else:
            self._log.warning('cannot enable clock: already closed.')

    # ..........................................................................
    def disable(self):
        if self._enabled:
            self._enabled = False
            self._thread = None
            self._log.info('clock disabled.')
        else:
            self._log.warning('already disabled.')

    # ..........................................................................
    def close(self):
        if not self._closed:
            if self._enabled:
                self.disable()
            time.sleep(0.3)
            self._closed = True
            self._log.info('closed.')
        else:
            self._log.warning('already closed.')

# ...............................................................
class Tick(Message):
    def __init__(self, eid, event, value):
        super().__init__(eid, Event.CLOCK_TICK, value)

# ...............................................................
class Tock(Message):
    def __init__(self, eid, event, value):
        super().__init__(eid, Event.CLOCK_TOCK, value)

#EOF
