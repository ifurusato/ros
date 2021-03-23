#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# Copyright 2020-2021 by Murray Altheim. All rights reserved. This file is part
# of the Robot Operating System project, released under the MIT License. Please
# see the LICENSE file included as part of this package.
#
# author:   Murray Altheim
# created:  2019-12-23
# modified: 2020-03-12
#

import itertools, string
import random
from datetime import datetime as dt

from colorama import init, Fore, Style
init()

# ..............

from lib.logger import Logger, Level
#from lib.message_factory import MessageFactory
from lib.message import Message
from lib.event import Event

# ..............................................................................
class MessageFactory(object):
    '''
    A factory for Messages.
    '''
    def __init__(self, message_bus=None, level=Level.INFO):
        self._log = Logger("msgfactory", level)
        self._message_bus = message_bus
        self._counter = itertools.count()
        self._choices = string.ascii_lowercase + string.digits
        self._log.info('ready.')

    # ..........................................................................
    def get_message(self, event, value):
        _host_id = "".join(random.choices(self._choices, k=4))
        _name = 'id-{}'.format(_host_id)
        _message = Message(instance_name=_name, event=event, value=value)
        if self._message_bus:
            _message.set_subscribers(self._message_bus.subscribers)
        return _message

#EOF
