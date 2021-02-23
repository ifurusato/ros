#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# Copyright 2020 by Murray Altheim. All rights reserved. This file is part of
# the Robot Operating System project and is released under the "Apache Licence,
# Version 2.0". Please see the LICENSE file included as part of this package.
#
# author:   Murray Altheim
# created:  2021-02-16
# modified: 2021-02-17
#

#import itertools
from colorama import init, Fore, Style
init()

from lib.event import Event
from lib.message_factory import MessageFactory
from lib.message import Message
from lib.message_bus import MessageBus
from lib.logger import Logger, Level

# ..............................................................................
class MockMessageBus(MessageBus):
    '''
    This message bus just displays IFS events as they arrive.
    '''
    def __init__(self, ifs, level):
        super().__init__(level)
        self._mlog = Logger('mbus', level)
#       self._count = 0
        self._ifs = ifs
#       self._counter = itertools.count()
#       self._log = Logger("message-bus", level)
        self._log.info('ready.')

    # ......................................................
    def handle(self, message: Message):
#       self._count = next(self._counter)
#       message.number = self._count
        _event = message.event
        self._mlog.info(Fore.BLUE + 'handling message #{}; priority {}: {}; event: {}'.format(message.number, message.priority, message.description, _event))
        if _event is Event.DECREASE_SPEED:
            self._mlog.info(Fore.YELLOW + 'decrease speed.')
        elif _event is Event.INCREASE_SPEED:
            self._mlog.info(Fore.YELLOW + 'increase speed.')
        elif _event != Event.CLOCK_TICK and _event != Event.CLOCK_TICK:
            # otherwise pass to IFS
            self._ifs.process_message(message)
        self._mlog.info(Fore.WHITE + 'passing message #{}; to superclass...'.format(message.number))
        super().handle(message)

#   # ......................................................
#   @property
#   def count(self):
#       return self._count

#EOF
