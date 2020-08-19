#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# Copyright 2020 by Murray Altheim. All rights reserved. This file is part of
# the Robot OS project and is released under the "Apache Licence, Version 2.0".
# Please see the LICENSE file included as part of this package.
#
# Note that the Infrareds class and this test are no longer being developed,
# as the functionality has been replaced by the IntegratedFrontSensor.
#

import time, sys, signal, threading, itertools
from colorama import init, Fore, Style
init()

from lib.devnull import DevNull
from lib.event import Event
from lib.logger import Level, Logger
from lib.config_loader import ConfigLoader
from lib.infrareds import Infrareds


# exception handler ........................................................
def signal_handler(signal, frame):
    print(Fore.RED + 'Ctrl-C caught: exiting...' + Style.RESET_ALL)
    if _infrareds is not None:
        _infrareds.close()
    sys.stderr = DevNull()
    print(Fore.MAGENTA + 'exit.' + Style.RESET_ALL)
    sys.exit(0)

# ..............................................................................
class MockMessageQueue():
    '''
        This message queue waits for at least one infrared event of each type.
    '''
    def __init__(self, level):
        super().__init__()
        self._counter = itertools.count()
        self._log = Logger("mock queue", Level.INFO)
        self._events = []
        self._events.append(Event.INFRARED_PORT)
        self._events.append(Event.INFRARED_CNTR)
        self._events.append(Event.INFRARED_STBD)
        self._events.append(Event.INFRARED_PORT_SIDE)
        self._events.append(Event.INFRARED_STBD_SIDE)
        self._events.append(Event.INFRARED_SHORT_RANGE)
        self._events.append(Event.INFRARED_LONG_RANGE)
        self._log.info('ready.')


    # ......................................................
    def add(self, message):
        message.set_number(next(self._counter))
        self._log.info('added message #{}: priority {}: {}'.format(message.get_number(), message.get_priority(), message.get_description()))
        event = message.get_event()
        # note that because we can't have both a CNTR digital sensor and the SHORT_RANGE/LONG_RANGE 
        # analog sensors, triggering one deletes the other
        if event is Event.INFRARED_PORT:
            if event in self._events:
                self._log.info(Fore.BLUE + Style.BRIGHT + 'INFRARED_PORT: {}'.format(event.description))
            self._remove_event(Event.INFRARED_PORT)
        elif event is Event.INFRARED_CNTR:
            if event in self._events:
                self._log.info(Fore.BLUE + Style.BRIGHT + 'INFRARED_PORT: {}'.format(event.description))
            self._remove_event(Event.INFRARED_CNTR)
            self._remove_event(Event.INFRARED_SHORT_RANGE)
            self._remove_event(Event.INFRARED_LONG_RANGE)
        elif event is Event.INFRARED_STBD:
            if event in self._events:
                self._log.info(Fore.BLUE + Style.BRIGHT + 'INFRARED_PORT: {}'.format(event.description))
            self._remove_event(Event.INFRARED_STBD)
        elif event is Event.INFRARED_PORT_SIDE:
            if event in self._events:
                self._log.info(Fore.BLUE + Style.BRIGHT + 'INFRARED_PORT: {}'.format(event.description))
            self._remove_event(Event.INFRARED_PORT_SIDE)
        elif event is Event.INFRARED_STBD_SIDE:
            if event in self._events:
                self._log.info(Fore.BLUE + Style.BRIGHT + 'INFRARED_PORT: {}'.format(event.description))
            self._remove_event(Event.INFRARED_STBD_SIDE)
        elif event is Event.INFRARED_SHORT_RANGE:
            if event in self._events:
                self._log.info(Fore.BLUE + Style.BRIGHT + 'INFRARED_PORT: {}'.format(event.description))
            self._remove_event(Event.INFRARED_SHORT_RANGE)
            self._remove_event(Event.INFRARED_CNTR)
        elif event is Event.INFRARED_LONG_RANGE:
            if event in self._events:
                self._log.info(Fore.BLUE + Style.BRIGHT + 'INFRARED_PORT: {}'.format(event.description))
            self._remove_event(Event.INFRARED_LONG_RANGE)
            self._remove_event(Event.INFRARED_CNTR)
        else:
            self._log.info(Fore.BLUE + Style.BRIGHT + 'other event: {}'.format(event.description))
        self._display_event_list()

    # ......................................................
    def is_complete(self):
        return not self._events

    # ......................................................
    def _display_event_list(self):
        self._log.info('\n' + Fore.BLUE + Style.BRIGHT + '{} events remain in list:'.format(len(self._events)))
        for e in self._events:
            self._log.info(Fore.BLUE + Style.BRIGHT + '{}'.format(e.description))

    # ......................................................
    def _remove_event(self, event):
        if event in self._events:
            self._events.remove(event)


# main .........................................................................
_infrareds = None

def main():

    signal.signal(signal.SIGINT, signal_handler)

    _log = Logger("infrareds test", Level.INFO)
    _log.info('starting test...')

    _log.info(Fore.YELLOW + Style.BRIGHT + 'Press Ctrl+C to exit.')
    _log.info(Fore.BLUE + Style.BRIGHT + 'to pass test, trigger all infrared sensors...')

    # read YAML configuration
    _loader = ConfigLoader(Level.INFO)
    filename = 'config.yaml'
    _config = _loader.configure(filename)
    
    _queue = MockMessageQueue(Level.INFO)

    _infrareds = Infrareds(_config, _queue, Level.INFO)
    _infrareds.enable()

    while not _queue.is_complete():
        _queue._display_event_list()
        time.sleep(2.0)

    _infrareds.close()
    _log.info('complete.')


if __name__== "__main__":
    main()

#EOF
