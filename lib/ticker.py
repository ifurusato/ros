#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# Copyright 2020-2021 by Murray Altheim. All rights reserved. This file is part
# of the Robot Operating System project, released under the MIT License. Please
# see the LICENSE file included as part of this package.
#
# author:   Murray Altheim
# created:  2020-05-19
# modified: 2020-11-06
#
# A simple clock that calls a callback on a regular basis. The clock
# frequency and callback function are passed as constructor arguments.
#

from threading import Thread
from colorama import init, Fore, Style
init()

from lib.logger import Logger, Level
from lib.rate import Rate

# ...............................................................
class Ticker(object):
    '''
    A simple threaded clock that executes a callback every loop.
    One or more subscribers can be added to the callback list.

    :param loop_freq_hz:   the loop frequency in Hertz
    :param callback:       the callback function
    :param level:          the optional log level
    '''
    def __init__(self, loop_freq_hz, callback, level=Level.INFO):
        super().__init__()
        self._log = Logger("clock", level)
        self._loop_freq_hz = loop_freq_hz
        self._rate         = Rate(self._loop_freq_hz)
        self._log.info('tick frequency: {:d}Hz'.format(self._loop_freq_hz))
        self._callbacks    = []
        self._thread       = None
        self._enabled      = False
        self._closed       = False
        self._log.info('ready.')

    # ..........................................................................
    def add_callback(self, callback):
        self._callbacks.append(callback)

    # ..........................................................................
    def name(self):
        return 'clock'

    # ..........................................................................
    @property
    def freq_hz(self):
        return self._loop_freq_hz

    # ..........................................................................
    def _loop(self, f_is_enabled):
        '''
        The clock loop, which executes while the f_is_enabled flag is True.
        '''
        while f_is_enabled():
            for callback in self._callbacks:
                self._log.debug('executing callback...')
                callback()
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
                    self._thread = Thread(name='clock', target=Ticker._loop, args=[self, lambda: self.enabled], daemon=True)
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
            self._closed = True
            self._log.info('closed.')
        else:
            self._log.warning('already closed.')

#EOF
