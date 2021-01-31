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
    A system clock that creates a "Tick" message every loop,
    alternating with a "Tock" message every modulo-nth loop.

    This passes its messages on to any added consumers, then
    on to the message bus.
    '''
    def __init__(self, config, message_bus, message_factory, level):
        super().__init__()
        self._message_bus = message_bus
        self._message_factory = message_factory
        self._log = Logger("clock", level)
        if config is None:
            raise ValueError('null configuration argument.')
        _config           = config['ros'].get('clock')
        _loop_freq_hz     = _config.get('loop_freq_hz')
        self._tock_modulo = _config.get('tock_modulo')
        self._bus_first   = _config.get('bus_first')
        self._log.info('tick frequency: {:d}Hz'.format(_loop_freq_hz))
        self._log.info('tock frequency: {:d}Hz'.format(round(_loop_freq_hz / self._tock_modulo)))
        self._counter     = itertools.count()
        self._rate        = Rate(_loop_freq_hz)
        self._consumers   = []
        self._thread      = None
        self._enabled     = False
        self._closed      = False
        self._tick_type   = type(Tick(None, Event.CLOCK_TICK, None))
        self._tock_type   = type(Tock(None, Event.CLOCK_TOCK, None))
        self._log.info('ready.')

    # ..........................................................................
    def add_consumer(self, consumer):
        '''
            Add a consumer to the optional list of message consumers.
        '''
        return self._consumers.append(consumer)

    # ..........................................................................
    def remove_consumer(self, consumer):
        '''
        Remove the consumer from the list of message consumers.
        '''
        try:
            self._consumers.remove(consumer)
        except ValueError:
            self._log.warn('message consumer was not in list.')

    # ..........................................................................
    def _loop(self, f_is_enabled):
        while f_is_enabled():
            _count = next(self._counter)
            if (( _count % self._tock_modulo ) == 0 ):
                _message = self._message_factory.get_message_of_type(self._tock_type, Event.CLOCK_TOCK, _count)
            else:
                _message = self._message_factory.get_message_of_type(self._tick_type, Event.CLOCK_TICK, _count)
            if self._bus_first: # first to message bus, then consumers
                self._message_bus.add(_message)
                for consumer in self._consumers:
                    consumer.add(_message);
            else: # first add to any consumers, then message bus
                for consumer in self._consumers:
                    consumer.add(_message);
                self._message_bus.add(_message)

#           time.sleep(0.003)
            self._rate.wait()
        self._log.info('exited clock loop.')

    # ..........................................................................
    @property
    def enabled(self):
        return self._enabled

    # ..........................................................................
    def enable(self):
        if not self._closed:
            self._enabled = True
            # if we haven't started the thread yet, do so now...
            if self._thread is None:
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
