#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# Copyright 2020 by Murray Altheim. All rights reserved. This file is part of
# the Robot OS project and is released under the "Apache Licence, Version 2.0".
# Please see the LICENSE file included as part of this package.
#
# author:   altheim
# created:  2020-01-18
# modified: 2020-02-06

import time, sys, signal, threading, itertools
from colorama import init, Fore, Style
init()

from lib.devnull import DevNull
from lib.event import Event
from lib.logger import Level
from lib.bumpers import Bumpers
from lib.config_loader import ConfigLoader


# exception handler ........................................................
def signal_handler(signal, frame):
    print(Fore.RED + 'Ctrl-C caught: exiting...' + Style.RESET_ALL)
    sys.stderr = DevNull()
    print(Fore.MAGENTA + 'exit.' + Style.RESET_ALL)
    sys.exit(0)

# ..............................................................................
class MockMessageQueue():
    '''
        This message queue waits for at least one bumper event of each type.
    '''
    def __init__(self, level):
        super().__init__()
        self._counter = itertools.count()
        self._events = []
        self._events.append(Event.BUMPER_PORT)
        self._events.append(Event.BUMPER_CENTER)
        self._events.append(Event.BUMPER_STBD)
        self._events.append(Event.BUMPER_UPPER)

    # ......................................................
    def add(self, message):
        message.set_number(next(self._counter))
        print('bumpers_test      :' + Fore.BLACK + ' INFO  : ADDED message #{}: priority {}: {}'.format(message.get_number(), message.get_priority(), message.get_description()) + Style.RESET_ALL)
        event = message.get_event()
        if event is Event.BUMPER_PORT:
            if event in self._events:
                print('bumpers_test      :' + Fore.BLUE + Style.BRIGHT + ' INFO  : BUMPER_PORT: {}'.format(event.description) + Style.RESET_ALL)
            self._remove_event(Event.BUMPER_PORT)
        elif event is Event.BUMPER_CENTER:
            if event in self._events:
                print('bumpers_test      :' + Fore.BLUE + Style.BRIGHT + ' INFO  : BUMPER_PORT: {}'.format(event.description) + Style.RESET_ALL)
            self._remove_event(Event.BUMPER_CENTER)
        elif event is Event.BUMPER_STBD:
            if event in self._events:
                print('bumpers_test      :' + Fore.BLUE + Style.BRIGHT + ' INFO  : BUMPER_PORT: {}'.format(event.description) + Style.RESET_ALL)
            self._remove_event(Event.BUMPER_STBD)
        elif event is Event.BUMPER_UPPER:
            if event in self._events:
                print('bumpers_test      :' + Fore.BLUE + Style.BRIGHT + ' INFO  : BUMPER_PORT: {}'.format(event.description) + Style.RESET_ALL)
            self._remove_event(Event.BUMPER_UPPER)
        else:
            print('bumpers_test      :' + Fore.BLUE + Style.BRIGHT + ' INFO  : other event: {}'.format(event.description) + Style.RESET_ALL)
        self._display_event_list()

    # ......................................................
    def is_complete(self):
        return not self._events

    # ......................................................
    def _display_event_list(self):
        print('\nbumpers_test      :' + Fore.BLUE + Style.BRIGHT + ' INFO  : {} events remain in list:'.format(len(self._events)) + Style.RESET_ALL)
        for e in self._events:
            print('bumpers_test      :' + Fore.BLUE + Style.BRIGHT + ' INFO  :     {}'.format(e.description) + Style.RESET_ALL)

    # ......................................................
    def _remove_event(self, event):
        if event in self._events:
            self._events.remove(event)


# main .........................................................................

def main():

    print('bumpers_test      :' + Fore.CYAN + ' INFO  : starting test...' + Style.RESET_ALL)

    print('bumpers_test      :' + Fore.YELLOW + Style.BRIGHT + ' INFO  : Press Ctrl+C to exit.' + Style.RESET_ALL)

    signal.signal(signal.SIGINT, signal_handler)

    print('bumpers_test      :' + Fore.BLUE + Style.BRIGHT + ' INFO  : to pass test, trigger all bumper sensors...' + Style.RESET_ALL)

    _queue = MockMessageQueue(Level.INFO)

    # read YAML configuration
    _loader = ConfigLoader(Level.INFO)
    filename = 'config.yaml'
    _config = _loader.configure(filename)

    _bumpers = Bumpers(_config, _queue, None, Level.INFO)

    _bumpers.enable()

    while not _queue.is_complete():
        _queue._display_event_list()
        time.sleep(2.0)

    _bumpers.close()


if __name__== "__main__":
    main()

#EOF
