#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# Copyright 2020-2021 by Murray Altheim. All rights reserved. This file is part
# of the Robot Operating System project, released under the MIT License. Please
# see the LICENSE file included as part of this package.
#
# author:   Murray Altheim
# created:  2021-03-10
# modified: 2021-03-16
#

import uuid
from datetime import datetime as dt
from colorama import init, Fore, Style
init()

from lib.logger import Logger, Level
from lib.event import Event

# ..............................................................................
class Message(object):
    '''
    Don't create one of these directly: use the MessageFactory class.
    '''
    def __init__(self, instance_name, event, value):
        self._timestamp     = dt.now()
        self._message_id    = uuid.uuid4()
        self._expectation   = -1 
        self._processed     = 0
        self._saved         = False
        self._expired       = False
        self._restarted     = False
        self.acked          = [] # list of subscriber's names who've acknowledged message
        self._instance_name = instance_name
        self._hostname      = '{}.acme.com'.format(self._instance_name)
        self._event         = event
        self._value         = value

    # timestamp     ............................................................

    @property
    def timestamp(self):
        return self._timestamp

    # message_id    ............................................................

    @property
    def message_id(self):
        return self._message_id

    # expectation   ............................................................

    @property
    def expectation_set(self):
        '''
        Returns True if the expectation has been set.
        '''
        return self._expectation >= 0

    def expect(self, count):
        '''
        Set the number of times the message is expected to be consumed.
        This is generally set to the number of subscribers.
        '''
        self._expectation = count

    # processed     ............................................................

    @property
    def processed(self):
        return self._processed

    def process(self):
        print(Fore.GREEN + '>>>>>> message process() event: {}'.format(self.event.description) + Style.RESET_ALL)
        self._processed += 1

    # saved         ............................................................

    @property
    def saved(self):
        return self._saved

    def save(self):
        self._saved = True

    # expired       ............................................................

    @property
    def expired(self):
        return self._expired

    def expire(self):
        self._expired = True

    # restarted       ..........................................................

    @property
    def restarted(self):
        return self._restarted

    def restart(self):
        self._restarted = True

    # acked         ............................................................

    @property
    def acknowledgements(self):
        return self.acked

    @property
    def acknowledged(self):
        '''
        Returns True if the message has been acknowledged by all subscribers.
        '''
        return len(self.acked) >= self.expectation

    def acknowledge(self, name):
        '''
        To be called by each subscriber, acknowledging receipt of the message.
        '''
        if not self.expectation_set:
            raise Exception('no expectation set ({}).'.format(self._instance_name))
        self.acked.append(name)
#       print('-- acknowledged {:d} times.'.format(self.acked) + Style.RESET_ALL)

    # instance_name ............................................................

    @property
    def name(self):
        '''
        Return the instance name of the message.
        '''
        return self._instance_name

    # hostname      ............................................................

    @property
    def hostname(self):
        '''
        Return the hostname of the message.
        '''
        return self._hostname

    # event         ............................................................

    @property
    def event(self):
        return self._event

    # value         ............................................................

    @property
    def value(self):
        return self._value

#EOF
