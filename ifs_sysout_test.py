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
#  This just displays IR messages from the Integrated Front Sensor to sysout.
#  Bumper messages are ignored.
#

import itertools, sys, time, traceback
from colorama import init, Fore, Style
init()

from lib.logger import Logger, Level
from lib.config_loader import ConfigLoader
from lib.event import Event
from lib.message import Message
from lib.message_factory import MessageFactory
from lib.message_bus import MessageBus
from lib.rate import Rate
from lib.clock import Clock
from lib.ifs import IntegratedFrontSensor

# ..............................................................................
class MessageHandler():
    '''
    This handler just displays IFS IR events as they arrive.
    '''
    def __init__(self, level):
        super().__init__()
        self._counter = itertools.count()
        self._log = Logger("queue", Level.INFO)
        self._ir = [ 'PSID', 'PORT', 'CNTR', 'STBD', 'SSID' ]
        self._log.info('ready.')

    # ......................................................
    def handle(self, message):
        self._log.debug('handle message #{}: priority {}: {}'.format(message.number, message.priority, message.description))
        _event = message.event
        self._ir[0] = Fore.RED   + Style.BRIGHT + 'PSID' if _event is Event.INFRARED_PORT_SIDE else Fore.BLACK + Style.DIM + '....'
        self._ir[1] = Fore.RED   + Style.NORMAL + 'PORT' if _event is Event.INFRARED_PORT      else Fore.BLACK + Style.DIM + '....'
        self._ir[2] = Fore.BLUE  + Style.BRIGHT + 'CNTR' if _event is Event.INFRARED_CNTR      else Fore.BLACK + Style.DIM + '....'
        self._ir[3] = Fore.GREEN + Style.NORMAL + 'STBD' if _event is Event.INFRARED_STBD      else Fore.BLACK + Style.DIM + '....'
        self._ir[4] = Fore.GREEN + Style.BRIGHT + 'SSID' if _event is Event.INFRARED_STBD_SIDE else Fore.BLACK + Style.DIM + '....'
        print('{} '.format(self._ir[0])    \
               + '{} '.format(self._ir[1]) \
               + '{} '.format(self._ir[2]) \
               + '{} '.format(self._ir[3]) \
               + '{} '.format(self._ir[4]) + Style.RESET_ALL, end='\n')

# ..............................................................................
def main():
    try:
        _log = Logger("test", Level.INFO)
        _log.info(Fore.BLUE + 'configuring...')
        _loader = ConfigLoader(Level.INFO)
        filename = 'config.yaml'
        _config = _loader.configure(filename)

        _message_factory = MessageFactory(Level.INFO)
        _message_bus = MessageBus(Level.INFO)
        _clock = Clock(_config, _message_bus, _message_factory, Level.WARN)
        _clock.enable()

        _ifs = IntegratedFrontSensor(_config, _clock, Level.INFO)
        _ifs.enable()

        _handler = MessageHandler(Level.INFO)
        _message_bus.add_handler(Message, _handler.handle)

        try:

            _log.info(Fore.BLUE + 'starting loop... type Ctrl-C to exit.')
            _rate = Rate(1)
#           while True:
            for i in range(360):
                _rate.wait()
            _log.info(Fore.BLUE + 'exited loop.')

        except KeyboardInterrupt:
            print(Fore.RED + 'Ctrl-C caught; exiting...' + Style.RESET_ALL)

    except Exception as e:
        print(Fore.RED + Style.BRIGHT + 'error: {}'.format(e))
        traceback.print_exc(file=sys.stdout)

if __name__== "__main__":
    main()

#EOF
