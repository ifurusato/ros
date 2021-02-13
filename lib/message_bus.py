#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# Copyright 2020 by Murray Altheim. All rights reserved. This file is part of
# the Robot OS project and is released under the "Apache Licence, Version 2.0".
# Please see the LICENSE file included as part of this package.
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
    sys.exit(Fore.RED + 'This script requires the pymessagebus module\nInstall with: sudo pip3 install "pymessagebus==1.*"' + Style.RESET_ALL)

from lib.message import Message
from lib.logger import Logger, Level

# ..............................................................................
class MessageBus():
    '''
    A message bus wrapper around PyMessageBus, this provides a simple
    centralised pub-sub-like framework for handling Message objects.
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
        self._log.info('added message handler \'{}()\' for type: {}'.format(type(handler), message_type.__name__))

    # ..........................................................................
    def handle(self, message: Message):
        '''
        Add a new Message to the message bus, and any associated handlers.
        '''
        self._message_bus.handle(message)
#       _result = self._message_bus.handle(message)
#       self._log.debug(Fore.BLACK + 'handle message eid#{}; priority={}; description: {};\t'.format(message.eid, message.priority, message.description) \
#               + Fore.WHITE + 'result: {}'.format(len(_result)))

#EOF
