#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# Copyright 2020-2021 by Murray Altheim. All rights reserved. This file is part
# of the Robot Operating System project, released under the MIT License. Please
# see the LICENSE file included as part of this package.
#
# author:   Murray Altheim
# created:  2021-03-10
# modified: 2021-03-13
#

import attr, uuid
from datetime import datetime as dt
from colorama import init, Fore, Style
init()

from lib.logger import Logger, Level
from lib.event import Event

# ..............................................................................
@attr.s
class Message:
    '''
    Don't create one of these directly: use the MessageFactory class.
    '''
    instance_name = attr.ib()
    message_id    = attr.ib(repr=False, default=str(uuid.uuid4()))
    timestamp     = attr.ib(repr=False, default=dt.now())
    hostname      = attr.ib(repr=False, init=False)
    acked         = attr.ib(repr=False, default=None) # count down to zero
    saved         = attr.ib(repr=False, default=False)
    processed     = attr.ib(repr=False, default=0)
    event         = attr.ib(repr=False, default=None)
    value         = attr.ib(repr=False, default=None)
    expired       = attr.ib(repr=False, default=False)

    def __attrs_post_init__(self):
        self.hostname = f"{self.instance_name}.example.net"

    @property
    def expected(self):
        return self.acked != None

    def expect(self, count):
        self.acked = count

    @property
    def fulfilled(self):
        return self.acked <= 0

    def acknowledge(self):
        if self.acked == None:
            raise Exception('no expectation set ({}).'.format(self.instance_name))
        self.acked -= 1
        print(Fore.WHITE + '>> acknowledged {:d} times.'.format(self.acked) + Style.RESET_ALL)

#EOF
