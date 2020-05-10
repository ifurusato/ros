#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# Copyright 2020 by Murray Altheim. All rights reserved. This file is part of
# the Robot OS project and is released under the "Apache Licence, Version 2.0".
# Please see the LICENSE file included as part of this package.
#

import time, sys, signal, threading, itertools
from colorama import init, Fore, Style
init()

from lib.devnull import DevNull
from lib.event import Event
from lib.logger import Level
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
        self._events = []
        self._events.append(Event.INFRARED_PORT)
        self._events.append(Event.INFRARED_CENTER)
        self._events.append(Event.INFRARED_STBD)
        self._events.append(Event.INFRARED_PORT_SIDE)
        self._events.append(Event.INFRARED_STBD_SIDE)
        self._events.append(Event.INFRARED_SHORT_RANGE)
        self._events.append(Event.INFRARED_LONG_RANGE)


    # ......................................................
    def add(self, message):
        message.set_number(next(self._counter))
        print('infrareds_test    :' + Fore.BLACK + ' INFO  : ADDED message #{}: priority {}: {}'.format(message.get_number(), message.get_priority(), message.get_description()) + Style.RESET_ALL)
        event = message.get_event()
        # note that because we can't have both a CENTER digital sensor and the SHORT_RANGE/LONG_RANGE 
        # analog sensors, triggering one deletes the other
        if event is Event.INFRARED_PORT:
            if event in self._events:
                print('infrareds_test    :' + Fore.BLUE + Style.BRIGHT + ' INFO  : INFRARED_PORT: {}'.format(event.description) + Style.RESET_ALL)
            self._remove_event(Event.INFRARED_PORT)
        elif event is Event.INFRARED_CENTER:
            if event in self._events:
                print('infrareds_test    :' + Fore.BLUE + Style.BRIGHT + ' INFO  : INFRARED_PORT: {}'.format(event.description) + Style.RESET_ALL)
            self._remove_event(Event.INFRARED_CENTER)
            self._remove_event(Event.INFRARED_SHORT_RANGE)
            self._remove_event(Event.INFRARED_LONG_RANGE)
        elif event is Event.INFRARED_STBD:
            if event in self._events:
                print('infrareds_test    :' + Fore.BLUE + Style.BRIGHT + ' INFO  : INFRARED_PORT: {}'.format(event.description) + Style.RESET_ALL)
            self._remove_event(Event.INFRARED_STBD)
        elif event is Event.INFRARED_PORT_SIDE:
            if event in self._events:
                print('infrareds_test    :' + Fore.BLUE + Style.BRIGHT + ' INFO  : INFRARED_PORT: {}'.format(event.description) + Style.RESET_ALL)
            self._remove_event(Event.INFRARED_PORT_SIDE)
        elif event is Event.INFRARED_STBD_SIDE:
            if event in self._events:
                print('infrareds_test    :' + Fore.BLUE + Style.BRIGHT + ' INFO  : INFRARED_PORT: {}'.format(event.description) + Style.RESET_ALL)
            self._remove_event(Event.INFRARED_STBD_SIDE)
        elif event is Event.INFRARED_SHORT_RANGE:
            if event in self._events:
                print('infrareds_test    :' + Fore.BLUE + Style.BRIGHT + ' INFO  : INFRARED_PORT: {}'.format(event.description) + Style.RESET_ALL)
            self._remove_event(Event.INFRARED_SHORT_RANGE)
            self._remove_event(Event.INFRARED_CENTER)
        elif event is Event.INFRARED_LONG_RANGE:
            if event in self._events:
                print('infrareds_test    :' + Fore.BLUE + Style.BRIGHT + ' INFO  : INFRARED_PORT: {}'.format(event.description) + Style.RESET_ALL)
            self._remove_event(Event.INFRARED_LONG_RANGE)
            self._remove_event(Event.INFRARED_CENTER)
        else:
            print('infrareds_test    :' + Fore.BLUE + Style.BRIGHT + ' INFO  : other event: {}'.format(event.description) + Style.RESET_ALL)
        self._display_event_list()

    # ......................................................
    def is_complete(self):
        return not self._events

    # ......................................................
    def _display_event_list(self):
        print('\ninfrareds_test    :' + Fore.BLUE + Style.BRIGHT + ' INFO  : {} events remain in list:'.format(len(self._events)) + Style.RESET_ALL)
        for e in self._events:
            print('infrareds_test    :' + Fore.BLUE + Style.BRIGHT + ' INFO  :     {}'.format(e.description) + Style.RESET_ALL)

    # ......................................................
    def _remove_event(self, event):
        if event in self._events:
            self._events.remove(event)


# main .........................................................................
_infrareds = None

def main():

    print('infrareds_test    :' + Fore.CYAN + ' INFO  : starting test...' + Style.RESET_ALL)

    print('infrareds_test    :' + Fore.YELLOW + Style.BRIGHT + ' INFO  : Press Ctrl+C to exit.' + Style.RESET_ALL)

    signal.signal(signal.SIGINT, signal_handler)

    print('infrareds_test    :' + Fore.BLUE + Style.BRIGHT + ' INFO  : to pass test, trigger all infrared sensors...' + Style.RESET_ALL)

    _queue = MockMessageQueue(Level.INFO)
    _infrareds = Infrareds(_queue, True, Level.INFO)
    _infrareds.enable()

    while not _queue.is_complete():
        _queue._display_event_list()
        time.sleep(2.0)

    _infrareds.close()

    print('infrareds_test    :' + Fore.CYAN + ' INFO  : test complete.' + Style.RESET_ALL)


if __name__== "__main__":
    main()

#EOF
