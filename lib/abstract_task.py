#!/usr/bin/env python3
# abstract task class
#
# Copyright 2020 by Murray Altheim. All rights reserved. This file is part of
# the Robot OS project and is released under the "Apache Licence, Version 2.0".
# Please see the LICENSE file included as part of this package.
#
# author:   Murray Altheim
# created:  2019-12-04
# modified: 2020-01-19

import sys, time, threading
from abc import ABC, abstractmethod
from colorama import init, Fore, Style
init()

#mport lib.import_gpio 
from lib.fsm import FiniteStateMachine
from lib.devnull import DevNull
from lib.logger import Logger, Level

# ..............................................................................
class AbstractTask(ABC, FiniteStateMachine, threading.Thread):
    '''
    An abstract task class implemented as a Finite State Machine (FSM),
    where transitions between states begin with an initial Start state,
    proceeding through a series of controlled state transitions until 
    a Terminal state is reached.

    The thread is started by a call to start() and terminated by close().
    The _enabled variable is controlled by enable() and disable().
    '''

    sleep_delay = 1  # seconds

    def __init__(self, task_name, priority, mutex, level=Level.INFO):
        super().__init__(task_name)
        super(FiniteStateMachine, self).__init__()
        threading.Thread.__init__(self)
        # initialise logger
        self.task_name = task_name
        self._log = Logger(task_name, level)
        self._log.debug(task_name + '__init__() initialising...')
        # initialise GPIO
        self._priority = priority
        self._mutex = mutex
        self._active = True  # set False only when closing task
        self._enabled = False  # enabled/disabled toggle
        self._closing = False
        self._number = -1
        self._log.debug(task_name + '__init__() ready.')

    def set_number(self, number):
        self._number = number

    def get_number(self):
        return self._number

    def get_priority(self):
        return self._priority

    def get_task_name(self):
        return self.task_name

    def __cmp__(self, other):
        return cmp(self._priority, other._priority)

    def __lt__(self, other):
        return self._priority < other._priority

    def is_active(self):
        return self._active and self.is_alive()

    def is_enabled(self):
        return self._enabled

    @abstractmethod
    def run(self):
        super(FiniteStateMachine, self).run()
        self._log.debug('started ' + self.task_name + '.')
        pass

    @abstractmethod
    def enable(self):
        super().enable()
#       super(FiniteStateMachine, self).enable()
        self._log.debug('enabled ' + self.task_name + '.')
        self._enabled = True
        pass

    @abstractmethod
    def disable(self):
        super().disable()
#       super(FiniteStateMachine, self).disable()
        self._enabled = False
        self._log.debug('disabled ' + self.task_name + '.')
        pass

    @abstractmethod
    def close(self):
        super().close()
        if not self._closing:
            self._closing = True
            self._active = False
            self._enabled = False
            self._log.critical('closing ' + self.task_name + '...')
            _n = 0
            while self.is_alive():
                _n = _n + 1
                self._log.info('joining thread of ' + self.task_name + '.')
                self.join(timeout=2.0)
                if self.task_name is 'os' and _n >= 3:
                    self._log.error(Fore.RED + Style.BRIGHT + 'waited too long: forced termination...')
                    sys.stderr = DevNull()
                    sys.exit()
                self._log.info('waiting ({:d}) for {} to terminate...'.format(_n, self.task_name))
                time.sleep(0.25)
    
            self._log.critical('closed ' + self.task_name + '.')
#           pass
        else:
            self._log.error('already closing ' + self.task_name + '.')

# EOF
