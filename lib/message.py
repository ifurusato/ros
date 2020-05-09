#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# Copyright 2020 by Murray Altheim. All rights reserved. This file is part of
# the Robot OS project and is released under the "Apache Licence, Version 2.0".
# Please see the LICENSE file included as part of this package.
#

from colorama import init, Fore, Style
init()

from lib.event import Event
from lib.enums import ActionState
from lib.fsm import IllegalStateError

# ..............................................................................
class Message(object):
    '''
        Wraps an Event in a Message indicating the intention to execute an Action.
    '''
    def __init__(self, event):
        self._event       = event
        self._description = event.description
        self._priority    = event.priority
        self._state       = ActionState.INIT
        self._value       = None

    # ......................................................
    def __cmp__(self, other):
        return cmp(self._priority, other._priority)


    # ......................................................
    def __eq__(self, other): 
        if not isinstance(other, Message):
            # don't attempt to compare against unrelated types
            return NotImplemented
        return self._event == other._event and self._priority == other._priority and self._value == other._value


    # state transitions ........................................................

    # ......................................................
    def start(self):
        if self._state is ActionState.INIT:
            self._state = ActionState.STARTED
        else:
            raise IllegalStateError('invalid transition in {} from {} to STARTED.'.format(self._event.description, self._state.name))


    # ......................................................
    def complete(self):
        if self._state is ActionState.STARTED:
            self._state = ActionState.COMPLETED
        else:
            raise IllegalStateError('invalid transition in {} from {} to COMPLETED.'.format(self._event.description, self._state.name))


    # ......................................................
    def interrupt(self):
        '''
            We don't pay attention to state transitions: just close it.
        '''
        print(Fore.MAGENTA + 'interrupted {} event from {} to CLOSED.'.format(self._event.description, self._state.name) + Style.RESET_ALL)
        self._state = ActionState.CLOSED


    # ......................................................
    def is_complete(self):
        return self._state is ActionState.COMPLETED or self._state is ActionState.CLOSED


    # ......................................................
    def get_state(self):
        return self._state


    # ......................................................
    def get_event(self):
        return self._event


    # ......................................................
    def set_value(self, value):
        '''
            A message can carry content, as a value.
        '''
        self._value = value


    # ......................................................
    def get_value(self):
        '''
            Return the message's value, if it has been set.
        '''
        return self._value


    # ..........................................................................


    # ......................................................
    def set_number(self, number):
        self._number = number


    # ......................................................
    def get_number(self):
        return self._number


    # ......................................................
    def get_priority(self):
        return self._priority


    # ......................................................
    def get_description(self):
        return '{}/{}'.format(self._event.name, self._description)


    # ......................................................
    def __lt__(self, other):
        return self._priority < other._priority

#EOF
