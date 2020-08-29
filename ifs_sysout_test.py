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

import sys, time, itertools, traceback
from colorama import init, Fore, Style
init()

from lib.logger import Logger, Level
from lib.config_loader import ConfigLoader
from lib.event import Event
from lib.queue import MessageQueue
from lib.ifs import IntegratedFrontSensor
from lib.indicator import Indicator

# ..............................................................................
class MockMessageQueue():
    '''
        This message queue just displays IFS events as they arrive.
    '''
    def __init__(self, level):
        super().__init__()
        self._counter = itertools.count()
        self._log = Logger("queue", Level.INFO)
        self._log.info('ready.')

    # ......................................................
    def add(self, message):
        message.set_number(next(self._counter))
        self._log.info('added message #{}: priority {}: {}'.format(message.get_number(), message.get_priority(), message.get_description()))
        event = message.get_event()
        if event is Event.INFRARED_PORT_SIDE:
            self._log.info(Fore.RED + Style.BRIGHT + 'INFRARED_PORT_SIDE: {}'.format(event.description))
        elif event is Event.INFRARED_PORT:
            self._log.info(Fore.MAGENTA + Style.BRIGHT + 'INFRARED_PORT: {}'.format(event.description))
        elif event is Event.INFRARED_CNTR:
            self._log.info(Fore.BLUE + Style.BRIGHT + 'INFRARED_PORT: {}'.format(event.description))
        elif event is Event.INFRARED_STBD:
            self._log.info(Fore.CYAN + Style.BRIGHT + 'INFRARED_PORT: {}'.format(event.description))
        elif event is Event.INFRARED_STBD_SIDE:
            self._log.info(Fore.GREEN + Style.BRIGHT + 'INFRARED_PORT: {}'.format(event.description))
        elif event is Event.BUMPER_PORT:
            self._log.info(Fore.RED + Style.BRIGHT + 'BUMPER_PORT: {}'.format(event.description))
        elif event is Event.BUMPER_CNTR:
            self._log.info(Fore.BLUE + Style.BRIGHT + 'BUMPER_CNTR: {}'.format(event.description))
        elif event is Event.BUMPER_STBD:
            self._log.info(Fore.GREEN + Style.BRIGHT + 'BUMPER_STBD: {}'.format(event.description))
        else:
            self._log.info(Fore.BLACK + Style.BRIGHT + 'other event: {}'.format(event.description))

# ..............................................................................
def main():
    try:
        # read YAML configuration
        _loader = ConfigLoader(Level.INFO)
        filename = 'config.yaml'
        _config = _loader.configure(filename)
        _queue = MockMessageQueue(Level.INFO)
        # or if we're using a normal MessageQueue, add indicator as message consumer
#       _indicator = Indicator(Level.INFO)
#       _queue.add_consumer(_indicator)

        _ifs = IntegratedFrontSensor(_config, _queue, Level.INFO)
        _ifs.enable() 
        while True:
            time.sleep(1.0)

    except KeyboardInterrupt:
        print(Fore.RED + 'Ctrl-C caught; exiting...' + Style.RESET_ALL)
    except Exception as e:
        print(Fore.RED + Style.BRIGHT + 'error: {}'.format(e))
        traceback.print_exc(file=sys.stdout)

if __name__== "__main__":
    main()

#EOF
