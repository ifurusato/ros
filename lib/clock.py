#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# Copyright 2020 by Murray Altheim. All rights reserved. This file is part of
# the Robot Operating System project and is released under the "Apache Licence,
# Version 2.0". Please see the LICENSE file included as part of this package.
#
# author:   Murray Altheim
# created:  2020-05-19
# modified: 2020-05-19
#
# A system clock.
#

import time, threading, itertools
from colorama import init, Fore, Style
init()

from lib.logger import Logger, Level
from lib.event import Event
from lib.rate import Rate


# ...............................................................
class Clock(object):
    '''
       A system clock that creates a "tick" message every 
       loop, a "tock" message every modulo-nth loop.
    '''
    def __init__(self, config, queue, message_factory, level):
        super().__init__()
        self._queue = queue
        self._message_factory = message_factory
        self._log = Logger("clock", level)
        _config           = config['ros'].get('clock')
        _loop_freq_hz     = _config.get('loop_freq_hz')
        self._tock_modulo = _config.get('tock_modulo')
        self._counter     = itertools.count()
        self._rate        = Rate(_loop_freq_hz)
        self._thread      = None
        self._enabled     = False
        self._closed      = False
        self._log.info('ready.')

    # ..........................................................................
    def _loop(self, f_is_enabled):
        while f_is_enabled:
            _count = next(self._counter)
            self._queue.add(self._message_factory.get_message(Event.CLOCK_TOCK if (( _count % self._tock_modulo ) == 0 ) else Event.CLOCK_TICK, _count))
            time.sleep(0.003)
            self._rate.wait()

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
                self._thread = threading.Thread(target=Clock._loop, args=[self, lambda: self.enabled])
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
            if self._thread is not None:
                self._thread.join(timeout=1.0)
                self._log.info('clock thread joined.')
                self._thread = None
            self._log.info('clock disabled.')

    # ..........................................................................
    def close(self):
        if not self._closed:
            if self._enabled:
                self.disable()
            time.sleep(0.3)
            self._closed = True
            self._log.info('closed.')

#EOF
