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

    Uses attrs, see: https://www.attrs.org/en/stable/
    '''
    instance_name = attr.ib()
    acked         = set() # list of subscriber's names who've acknowledged message
    message_id    = attr.ib(repr=False, default=str(uuid.uuid4()))
    timestamp     = attr.ib(repr=False, default=dt.now())
    hostname      = attr.ib(repr=False, init=False)
    expectation   = attr.ib(repr=False, default=-1) 
    processed     = attr.ib(repr=False, default=0)
    saved         = attr.ib(repr=False, default=False)
    event         = attr.ib(repr=False, default=None)
    value         = attr.ib(repr=False, default=None)
    expired       = attr.ib(repr=False, default=False)

    def __attrs_post_init__(self):
        self.hostname = '{}.acme.com'.format(self.instance_name)

    @property
    def name(self):
        '''
        Return the instance name of the message.
        '''
        return self.instance_name

    @property
    def expectation_set(self):
        '''
        Returns True if the expectation has been set.
        '''
        return self.expectation >= 0

    def expect(self, count):
        '''
        Set the number of times the message is expected to be consumed.
        This is generally set to the number of subscribers.
        '''
        self.expectation = count

    @property
    def fulfilled(self):
        '''
        Returns True if the message has been acknowledged by all subscribers.
        '''
        return len(self.acked) >= self.expectation

    def acknowledge(self, name):
        '''
        To be called by each subscriber, acknowledging receipt of the message.
        '''
        if not self.expectation_set:
            raise Exception('no expectation set ({}).'.format(self.instance_name))
        self.acked.add(name)
#       print('-- acknowledged {:d} times.'.format(self.acked) + Style.RESET_ALL)

    @property
    def acknowledgements(self):
        return self.acked

#EOF
