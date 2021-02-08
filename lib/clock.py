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

import time, itertools
from datetime import datetime as dt
from threading import Thread
from colorama import init, Fore, Style
init()

from lib.message import Message
from lib.logger import Logger, Level
from lib.event import Event
from lib.rate import Rate

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
        self._counter      = itertools.count()
        self._rate         = Rate(self._loop_freq_hz)
        self._tick_type    = type(Tick(None, Event.CLOCK_TICK, None))
        self._tock_type    = type(Tock(None, Event.CLOCK_TOCK, None))
        self._log.info('tick frequency: {:d}Hz'.format(self._loop_freq_hz))
        self._log.info('tock frequency: {:d}Hz'.format(round(self._loop_freq_hz / self._tock_modulo)))
        self._enable_trim  = _config.get('enable_trim')
        self._log.info('trim enabled.' if self._enable_trim else 'trim disabled.')
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
        while f_is_enabled():

            _now = dt.now()

            _count = next(self._counter)
            if (( _count % self._tock_modulo ) == 0 ):
                _message = self._message_factory.get_message_of_type(self._tock_type, Event.CLOCK_TOCK, _count)
            else:
                _message = self._message_factory.get_message_of_type(self._tick_type, Event.CLOCK_TICK, _count)
            self._message_bus.add(_message)

            _delta_s = (_now - self._last_time).total_seconds()
            _delta_ms = _delta_s * 1000.0
            _error_s = (self.dt_ms / 1000.0) - _delta_s
            if self._enable_trim:
                self._rate.trim = -0.5 * _error_s

            # display stats
            if _delta_ms > -50.050 and _delta_ms < 50.050:
                self._log.info(Fore.GREEN  + 'dt: {:8.5f}ms; delta {:8.5f}ms; error: {:8.5f}ms; '.format(self.dt_ms, _delta_ms, _error_s * 1000.0) \
                        + Fore.BLUE + ' trim: {:9.6f}'.format(self._rate.trim))
            else:
                self._log.info(Fore.YELLOW + 'dt: {:8.5f}ms; delta {:8.5f}ms; error: {:8.5f}ms; '.format(self.dt_ms, _delta_ms, _error_s * 1000.0) \
                        + Fore.BLUE + ' trim: {:9.6f}'.format(self._rate.trim))

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
