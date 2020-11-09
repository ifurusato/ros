#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# Copyright 2020 by Murray Altheim. All rights reserved. This file is part of
# the Robot OS project and is released under the "Apache Licence, Version 2.0".
# Please see the LICENSE file included as part of this package.
#
# author:   Murray Altheim
# created:  2020-11-05
# modified: 2020-11-05
#
# https://github.com/DrBenton/pymessagebus

#from flask import jsonify

import sys, time, traceback

from colorama import init, Fore, Style
init()

from lib.config_loader import ConfigLoader
from lib.clock import Clock, Tick, Tock
from lib.queue import MessageQueue
from lib.message_bus import MessageBus
from lib.message_factory import MessageFactory
from lib.message import Message
from lib.logger import Logger, Level

from lib.ifs import IntegratedFrontSensor

# ..............................................................................
class MessageHandler(object):

    def __init__(self, level):
        super().__init__()
        self._log = Logger('msg-hand', level)
        self._log.info('ready.')

    # ..........................................................................
    def add(self, message):
        event = message.event
        self._log.info(Fore.MAGENTA + 'rx message: {}; event: {}; value: {:>5.2f}'.format(\
                message.description, event.description, message.value))
        if event is Event.INFRARED_PORT_SIDE:
            self._log.info(Fore.RED + Style.BRIGHT   + 'event: {};\tvalue: {:5.2f}cm'.format(event.description, message.value))
        elif event is Event.INFRARED_PORT:
            self._log.info(Fore.RED + Style.BRIGHT   + 'event: {};\tvalue: {:5.2f}cm'.format(event.description, message.value))
        elif event is Event.INFRARED_CNTR:
            self._log.info(Fore.BLUE + 'INFRARED_CNTR RECEIVED;\tvalue: {:5.2f}cm'.format(message.value))
        elif event is Event.INFRARED_STBD:
            self._log.info(Fore.GREEN + Style.BRIGHT + 'event: {};\tvalue: {:5.2f}cm'.format(event.description, message.value))
        elif event is Event.INFRARED_STBD_SIDE:
            self._log.info(Fore.GREEN + Style.BRIGHT + 'event: {};\tvalue: {:5.2f}cm'.format(event.description, message.value))
        else:
            pass
        pass


# ..............................................................................
class TickHandler(object):

    def __init__(self, ifs, level):
        super().__init__()
        self._ifs = ifs
        self._log = Logger('tick-hand', level)
        self._log.info('ready.')

    # ..........................................................................
    def tick(self, message):
#       self._log.info(Fore.GREEN + 'th.rx tick: {}::{}'.format(message.description, message.value))
#       self._ifs.add(message)
        pass

    # ..........................................................................
    def tock(self, message):
        self._log.debug(Fore.GREEN + Style.BRIGHT + 'th.rx tock: {}::{}'.format(message.description, message.value))
        pass


# main .........................................................................
def main(argv):

    try:

        # read YAML configuration
        _loader = ConfigLoader(Level.INFO)
        filename = 'config.yaml'
        _config = _loader.configure(filename)

        _message_factory = MessageFactory(Level.INFO)
        _queue = MessageQueue(_message_factory, Level.INFO)

        _msg_handler = MessageHandler(Level.INFO)
#       _tick_handler = TickHandler(_ifs, Level.INFO)

        # create message bus...
        _message_bus = MessageBus(Level.INFO)
        _message_bus.add_handler(Message, _msg_handler.add)
#       _message_bus.add_handler(Tick, _tick_handler.tick)
#       _message_bus.add_handler(Tock, _tick_handler.tock)
#       _message_bus.add_handler(Tick, _tick_handler.add)
#       _message_bus.add_consumer(_ifs)

        _clock = Clock(_config, _message_bus, _message_factory, Level.INFO)
        _ifs = IntegratedFrontSensor(_config, _queue, _clock, _message_bus, _message_factory, Level.INFO)

        _clock.enable()
        _ifs.enable()

        while True:
            time.sleep(1.0)

    except KeyboardInterrupt:
        print(Fore.CYAN + Style.BRIGHT + 'caught Ctrl-C; exiting...')
        
    except Exception:
        print(Fore.RED + Style.BRIGHT + 'error starting ros: {}'.format(traceback.format_exc()) + Style.RESET_ALL)

# call main ....................................................................
if __name__== "__main__":
    main(sys.argv[1:])

# prevent Python script from exiting abruptly
#signal.pause()

#EOF
#EOF
