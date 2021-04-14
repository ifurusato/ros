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
# NOTE: to guarantee exactly-once delivery each message must contain a list
# of the identifiers for all current subscribers, with each subscriber 
# acknowledgement removing it from that list.
#

import string, uuid, random
from datetime import datetime as dt
from colorama import init, Fore, Style
init()

from lib.logger import Logger, Level
from lib.event import Event
#from lib.subscriber import Subscriber

ID_CHARACTERS = string.ascii_uppercase + string.digits

# ..............................................................................
class Message(object):
    '''
    Don't create one of these directly: use the MessageFactory class.
    '''
    def __init__(self, event, value):
        self._timestamp     = dt.now()
        self._message_id    = uuid.uuid4()
        # generate instance name
        _host_id = "".join(random.choices(ID_CHARACTERS, k=4))
        _instance_name = 'id-{}'.format(_host_id)
        self._instance_name = _instance_name
        self._hostname      = '{}.acme.com'.format(self._instance_name)
        self._event         = event
        self._value         = value
        self._processed     = 0
        self._saved         = 0
        self._restarted     = 0
        self._expired       = False
        self._gc            = False
        self._subscribers   = {} # list of subscriber's names who've acknowledged message

    # timestamp     ............................................................

    @property
    def timestamp(self):
        return self._timestamp

    # age      .................................................................

    @property
    def age(self):
        _age_ms = (dt.now() - self._timestamp).total_seconds() * 1000.0
#       print(Fore.GREEN + Style.BRIGHT + 'message age: {:5.2f}ms ({})'.format(_age_ms, self._event.description) + Style.RESET_ALL)
        return int(_age_ms)

    # message_id    ............................................................

    @property
    def message_id(self):
        return self._message_id

    # processed     ............................................................

    @property
    def processed(self):
        return self._processed

    def process(self):
        self._processed += 1

    # saved         ............................................................

    @property
    def saved(self):
        return self._saved

    def save(self):
        self._saved += 1

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
        self._restarted += 1

    # garbage collection   .....................................................

    @property
    def gcd(self):
        return self._gc

    def gc(self):
        '''
        Garbage collect this message. This sets the 'gc' flag and nullifies
        the event and value properties so no further processing is possible.
        '''
        print(Fore.BLUE + 'gc: {}'.format(self.name) + Style.RESET_ALL)
        if self._gc:
            raise Exception('already garbage collected.')
        self._event = None
        self._value = None
        self._gc = True

    # acknowledged  ............................................................

    def print_acks(self):
        '''
        Returns a pretty-printed list of subscribers that have acknowledged
        this message.
        '''
        _list = []
        for subscriber in self._subscribers:
            _list.append('{} '.format(subscriber.name))
        return ''.join(_list)

    @property
    def expectation_set(self):
        '''
        Returns True if the expectation has been set.
        '''
        return len(self._subscribers) > 0

    @property
    def acknowledgements(self):
        return self._subscribers

    @property
    def unacknowledged_count(self):
        _count = 0
        for subscriber in self._subscribers:
            if not self._subscribers[subscriber]:
                _count += 1
        return _count

    def set_subscribers(self, subscribers):
        for subscriber in subscribers:
#           print(Fore.GREEN + 'subscriber {} ADDED to message {}.'.format(subscriber.name, self.name) + Style.RESET_ALL)
            self._subscribers[subscriber] = False

    @property
    def fully_acknowledged(self):
        '''
        Returns True if the message has been acknowledged by all subscribers,
        i.e., no subscriber flags remain set as False.
        '''
        for subscriber in self._subscribers:
            if not self._subscribers[subscriber]:
                return False
        return True

    def acknowledged_by(self, subscriber):
        '''
        Returns True if the message has been acknowledged by the specified subscriber.
        '''
        for subscr in self._subscribers:
            if subscr == subscriber and self._subscribers[subscriber] == True:
#               print(Fore.GREEN + 'acknowledged_by subscriber {} ADDED to message {}; return True.'.format(subscriber.name, self.name) + Style.RESET_ALL)
                return True
#       print(Fore.RED + 'acknowledged_by subscriber {} ADDED to message {}; return False.'.format(subscriber.name, self.name) + Style.RESET_ALL)
        return False

    def acknowledge(self, subscriber):
        '''
        To be called by each subscriber, acknowledging receipt of the message.
        '''
#       if not isinstance(subscriber, Subscriber):
#           raise Exception('expected subscriber, not {}.'.format(type(subscriber)))
        if not self.expectation_set:
            raise Exception('no subscriber expectations set ({}).'.format(self._instance_name))
        if self._subscribers[subscriber]:
            print(Style.DIM + 'message {} already acknowledged by subscriber: {}'.format(self.name, subscriber.name) + Style.RESET_ALL)
#           raise Exception('message {} already acknowledged by subscriber: {}'.format(self.name, subscriber.name))
        else:
#           print(Style.DIM + 'message {} acknowledged by subscriber {}; {:d} unacknowledged.'.format(self.name, subscriber.name, self.unacknowledged_count) + Style.RESET_ALL)
            self._subscribers[subscriber] = True

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
