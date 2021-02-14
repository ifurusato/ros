#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# Copyright 2020 by Murray Altheim. All rights reserved. This file is part
# of the pimaster2ardslave project and is released under the MIT Licence;
# please see the LICENSE file included as part of this package.
#
# author:   Murray Altheim
# created:  2020-04-30
# modified: 2020-05-24
#
#  This just displays messages from the Integrated Front Sensor to sysout.
#

import itertools, sys, threading, time, traceback
from colorama import init, Fore, Style
init()

from lib.logger import Logger, Level
from lib.config_loader import ConfigLoader
from lib.event import Event
from lib.message import Message
from lib.message_factory import MessageFactory
from lib.message_bus import MessageBus
from lib.clock import Clock
from lib.queue import MessageQueue
from lib.ifs import IntegratedFrontSensor

# ..............................................................................
class MockMessageQueue():
    '''
        This message queue just displays IFS events as they arrive.
    '''
    def __init__(self, level):
        super().__init__()
        self._counter = itertools.count()
        self._log = Logger("queue", Level.INFO)
        self._listeners = []
        self._log.info('ready.')

    # ..........................................................................
    def add_listener(self, listener):
        '''
        Add a listener to the optional list of message listeners.
        '''
        return self._listeners.append(listener)

    # ..........................................................................
    def remove_listener(self, listener):
        '''
        Remove the listener from the list of message listeners.
        '''
        try:
            self._listeners.remove(listener)
        except ValueError:
            self._log.warn('message listener was not in list.')

    # ......................................................
    def add(self, message):
        message.set_number(next(self._counter))
        self._log.debug('added message #{}: priority {}: {}'.format(message.get_number(), message.get_priority(), message.get_description()))
        _event = message.get_event()
        _value = message.value

        if _event is Event.INFRARED_PORT_SIDE:
            self._log.debug(Fore.RED + Style.BRIGHT + '> INFRARED_PORT_SIDE: {}; value: {}'.format(_event.description, _value))
        elif _event is Event.INFRARED_PORT_SIDE_FAR:
            self._log.debug(Fore.RED + Style.NORMAL + '> INFRARED_PORT_SIDE_FAR: {}; value: {}'.format(_event.description, _value))

        elif _event is Event.INFRARED_PORT:
            self._log.debug(Fore.MAGENTA + Style.BRIGHT + '> INFRARED_PORT: {}; value: {}'.format(_event.description, _value))
        elif _event is Event.INFRARED_PORT_FAR:
            self._log.debug(Fore.MAGENTA + Style.NORMAL + '> INFRARED_PORT_FAR: {}; value: {}'.format(_event.description, _value))
        # ..........................................................................................

        elif _event is Event.INFRARED_CNTR:
            self._log.info(Fore.BLUE + Style.BRIGHT + '> INFRARED_CNTR:     distance: {:>5.2f}cm'.format(_value))

        elif _event is Event.INFRARED_CNTR_FAR:
            self._log.info(Fore.BLUE + Style.NORMAL + '> INFRARED_CNTR_FAR: distance: {:5.2f}cm'.format(_value))

        # ..........................................................................................
        elif _event is Event.INFRARED_STBD:
            self._log.debug(Fore.CYAN + Style.BRIGHT + '> INFRARED_STBD: {}; value: {}'.format(_event.description, _value))
        elif _event is Event.INFRARED_STBD_FAR:
            self._log.debug(Fore.CYAN + Style.NORMAL + '> INFRARED_STBD_FAR: {}; value: {}'.format(_event.description, _value))

        elif _event is Event.INFRARED_STBD_SIDE:
            self._log.debug(Fore.GREEN + Style.BRIGHT + '> INFRARED_STBD_SIDE: {}; value: {}'.format(_event.description, _value))
        elif _event is Event.INFRARED_STBD_SIDE_FAR:
            self._log.debug(Fore.GREEN + Style.NORMAL + '> INFRARED_STBD_SIDE_FAR: {}; value: {}'.format(_event.description, _value))

#       elif _event is Event.BUMPER_PORT:
#           self._log.debug(Fore.RED + Style.BRIGHT + 'BUMPER_PORT: {}'.format(_event.description))
#       elif _event is Event.BUMPER_CNTR:
#           self._log.debug(Fore.BLUE + Style.BRIGHT + 'BUMPER_CNTR: {}'.format(_event.description))
#       elif _event is Event.BUMPER_STBD:
#           self._log.debug(Fore.GREEN + Style.BRIGHT + 'BUMPER_STBD: {}'.format(_event.description))
#       else:
#           self._log.debug(Fore.BLACK + Style.BRIGHT + 'other event: {}'.format(_event.description))

        # we're finished, now add to any listeners
        for listener in self._listeners:
            listener.add(message);

# ..............................................................................
def main():
    try:
        _log = Logger("test", Level.INFO)
        _log.info(Fore.BLUE + 'configuring...')

        # read YAML configuration
        _loader = ConfigLoader(Level.INFO)
        filename = 'config.yaml'
        _config = _loader.configure(filename)
        _queue = MockMessageQueue(Level.INFO)

        _message_factory = MessageFactory(Level.INFO)
        _message_bus = MessageBus(Level.INFO)
        _clock = Clock(_config, _message_bus, _message_factory, Level.WARN)
        _clock.enable()

        _ifs = IntegratedFrontSensor(_config, _clock, _message_bus, _message_factory, Level.INFO)
        _ifs.enable()

        try:

            _log.info(Fore.BLUE + 'starting...')

            for i in range(360):
                _log.info(Fore.BLUE + '{:d}; looping...'.format(i))
                time.sleep(1.0)

            _log.info(Fore.BLUE + 'exited loop.')

        except KeyboardInterrupt:
            print(Fore.RED + 'Ctrl-C caught; exiting...' + Style.RESET_ALL)

    except Exception as e:
        print(Fore.RED + Style.BRIGHT + 'error: {}'.format(e))
        traceback.print_exc(file=sys.stdout)

if __name__== "__main__":
    main()

#EOF
