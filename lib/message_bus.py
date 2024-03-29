#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# Copyright 2020-2021 by Murray Altheim. All rights reserved. This file is part
# of the Robot Operating System project, released under the MIT License. Please
# see the LICENSE file included as part of this package.
#
# author:   Murray Altheim
# created:  2020-11-05
# modified: 2021-02-08
#
# https://pypi.org/project/pymessagebus/
# https://github.com/DrBenton/pymessagebus
#

import sys, time, traceback
from colorama import init, Fore, Style
init()
try:
    from pymessagebus import MessageBus as PyMessageBus
except ImportError:
    sys.exit(Fore.RED + 'This script requires the pymessagebus module\nInstall with: pip3 install --user "pymessagebus==1.*"' + Style.RESET_ALL)

from lib.event import Event
from lib.message import Message
from lib.logger import Logger, Level

# ..............................................................................
class MessageBus():
    '''
    A message bus wrapper around PyMessageBus, this provides a simple,
    pub-sub-like framework for handling Message objects.

    Note that this is a synchronous bus and handle() blocks until the
    callback returns.
    '''
    def __init__(self, level):
        super().__init__()
        self._log = Logger('bus', level)
        self._log.info('initialised MessageBus...')
        self._message_bus = PyMessageBus()
        self._log.info('ready.')

    # ..........................................................................
    def add_handler(self, message_type, handler):
        '''
        Add a handler to the message bus for the given message type.
        '''
        self._message_bus.add_handler(message_type, handler)
        self._log.info(Fore.YELLOW + 'added message handler \'{}()\' for type: {}'.format(type(handler), message_type.__name__))

    # ..........................................................................
    def handle(self, message: Message):
        '''
        Add a new Message to the message bus, and any associated handlers.
        '''
#       self._log.info(Fore.BLACK + 'HANDLE message eid#{}; priority={}; description: {}'.format(message.eid, message.priority, message.description))
        _result = self._message_bus.handle(message)
        if ( message.event is not Event.CLOCK_TICK and message.event is not Event.CLOCK_TOCK ):
            self._log.info(Fore.BLACK + 'RESULT: {} ({}); event: {}'.format(_result, len(_result), message.event))

#EOF
