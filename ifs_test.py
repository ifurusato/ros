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
# This tests a hardware configuration of one button, one LED, two digital
# and one analog infrared sensors, first configuring the Arduino and then
# performing a communications loop.
#
# This requires installation of pigpio, e.g.:
#
#   % sudo pip3 install pigpio
#

import itertools
from colorama import init, Fore, Style
init()

from lib.logger import Logger, Level
from lib.config_loader import ConfigLoader
from lib.event import Event
from lib.queue import MessageQueue
from lib.ifs import IntegratedFrontSensor

_ifs = None

# ..............................................................................
class MockMessageQueue():
    '''
        This message queue waits for one CAT_SCAN event.
    '''
    def __init__(self, level):
        super().__init__()
        self._log = Logger("mock-queue", Level.INFO)
        self._counter = itertools.count()
        self._experienced_event = False

    # ......................................................
    def add(self, message):
        message.set_number(next(self._counter))
        self._log.debug('added message #{}: priority {}: {}'.format(message.get_number(), message.get_priority(), message.get_description()))
        event = message.get_event()
        if event is Event.INFRARED_STBD_SIDE:
            self._log.info(Fore.GREEN + Style.BRIGHT + 'event: {};\tvalue: {:d}'.format(event.description, message.get_value()))
        elif event is Event.INFRARED_STBD:
            self._log.info(Fore.GREEN + Style.BRIGHT + 'event: {};\tvalue: {:d}'.format(event.description, message.get_value()))
        elif event is Event.INFRARED_CENTER:
            self._log.info(Fore.BLUE + Style.BRIGHT + 'event: {};\tvalue: {:d}'.format(event.description, message.get_value()))
        elif event is Event.INFRARED_PORT:
            self._log.info(Fore.RED + Style.BRIGHT + 'event: {};\tvalue: {:d}'.format(event.description, message.get_value()))
        elif event is Event.INFRARED_PORT_SIDE:
            self._log.info(Fore.RED + Style.BRIGHT + 'event: {};\tvalue: {:d}'.format(event.description, message.get_value()))
        else:
            self._log.info(Fore.RED + 'other event: {}'.format(event.description))

    # ......................................................
    def is_complete(self):
        return self._experienced_event


# ..............................................................................
def main():

    try:

        # read YAML configuration
        _loader = ConfigLoader(Level.INFO)
        filename = 'config.yaml'
        _config = _loader.configure(filename)
        _queue = MockMessageQueue(Level.INFO)
#       _queue = MessageQueue(Level.INFO)

        _ifs = IntegratedFrontSensor(_config, _queue, Level.INFO)
        _ifs.enable() 

    except KeyboardInterrupt:
        self._log.warning('Ctrl-C caught; exiting...')
    finally:
        if _ifs is not None:
            _ifs.close()


if __name__== "__main__":
    main()

#EOF
