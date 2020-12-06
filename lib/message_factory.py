#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# Copyright 2020 by Murray Altheim. All rights reserved. This file is part of
# the Robot OS project and is released under the "Apache Licence, Version 2.0".
# Please see the LICENSE file included as part of this package.
#
# author:   Murray Altheim
# created:  2020-05-09
# modified: 2020-11-07
#

import itertools

from lib.logger import Logger, Level
from lib.message import Message

# ..............................................................................
class MessageFactory(object):

    def __init__(self, level):
        self._log = Logger("msgfactory", level)
        self._counter = itertools.count()
        self._log.info('ready.')
 
    # ..........................................................................
    def get_message(self, event, value):
        return Message(next(self._counter), event, value)

    # ..........................................................................
    def get_message_of_type(self, message_type, event, value):
        return message_type(next(self._counter), event, value)

#EOF
