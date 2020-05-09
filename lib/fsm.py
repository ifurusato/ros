#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# Copyright 2020 by Murray Altheim. All rights reserved. This file is part of
# the Robot OS project and is released under the "Apache Licence, Version 2.0".
# Please see the LICENSE file included as part of this package.
#
# author:   Murray Altheim
# created:  2020-01-19
# modified: 2020-02-13

from enum import Enum

from .logger import Logger, Level

level = Level.INFO

class State(Enum):
    NONE     = 0
    INITIAL  = 1
    STARTED  = 2
    ENABLED  = 3
    DISABLED = 4
    CLOSED   = 5

class IllegalStateError(RuntimeError):
    pass

class FiniteStateMachine():
    '''
        Implementation of a Finite State Machine (FSM).

        This basically permits an initial run() followed by repeated transitions
        between enable() and disable(), followed by a terminal close().
    '''

    # ..........................................................................
    def __init__(self,task_name):
        self.state = State.NONE
        self.task_name = task_name
        logger_name = "fsm:" + task_name
        self._log = Logger(logger_name, level)
        FiniteStateMachine.__transition__(self,State.INITIAL)
        self._log.debug('fsm initialised.')
        

    # ..........................................................................
    def __transition__(self,next_state):
        '''
            This method provides the functionality of a transition table, throwing
            exceptions or logging warnings if the transition is either invalid or
            ill-advised (resp.).
        '''
        self._log.debug('transition in {} from {} to {}.'.format(self.task_name, self.state, next_state))
        # transition table:
        if self.state is State.NONE:
            if next_state is State.INITIAL:
                pass
            else:
                raise IllegalStateError('invalid transition in {} from {} to {} (expected INITIAL).'.format(self.task_name, self.state, next_state))
        if self.state is State.INITIAL:
            if any([ next_state is State.STARTED, next_state is State.CLOSED ]):
                pass
            else:
                raise IllegalStateError('invalid transition in {} from {} to {} (expected STARTED).'.format(self.task_name, self.state, next_state))
        elif self.state is State.STARTED:
            if any([ next_state is State.ENABLED, next_state is State.DISABLED, next_state is State.CLOSED ]):
                pass
            else:
                raise IllegalStateError('invalid transition in {} from {} to {} (expected ENABLED, DISABLED, or CLOSED).'.format(self.task_name, self.state, next_state))
        elif self.state is State.ENABLED:
            if any([ next_state is State.DISABLED, next_state is State.CLOSED ]):
                pass
            elif next_state is State.ENABLED:
                self._log.warning('suspect transition in {} from {} to {}.'.format(self.task_name, self.state, next_state))
            else:
                raise IllegalStateError('invalid transition in {} from {} to {} (expected DISABLED or CLOSED).'.format(self.task_name, self.state, next_state))
        elif self.state is State.DISABLED:
            if any([ next_state is State.ENABLED, next_state is State.CLOSED ]):
                pass
            elif next_state is State.DISABLED:
                self._log.warning('suspect transition in {} from {} to {}.'.format(self.task_name, self.state, next_state))
            else:
                raise IllegalStateError('invalid transition in {} from {} to {} (expected ENABLED or CLOSED).'.format(self.task_name, self.state, next_state))
        elif self.state is State.CLOSED:
            raise IllegalStateError('invalid transition in {} from {} to {} (already CLOSED).'.format(self.task_name, self.state, next_state))
        self.state = next_state


    # ..........................................................................
    def run(self):
        self._log.debug('run.')
        FiniteStateMachine.__transition__(self,State.STARTED)


    # ..........................................................................
    def enable(self):
        self._log.debug('enable.')
        FiniteStateMachine.__transition__(self,State.ENABLED)


    # ..........................................................................
    def disable(self):
        self._log.debug('disable.')
        FiniteStateMachine.__transition__(self,State.DISABLED)


    # ..........................................................................
    def close(self):
        self._log.debug('close.')
        FiniteStateMachine.__transition__(self,State.CLOSED)

#EOF
