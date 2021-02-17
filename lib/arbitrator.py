#!/usr/bin/env python3
#
# Copyright 2020 by Murray Altheim. All rights reserved. This file is part of
# the Robot OS project and is released under the "Apache Licence, Version 2.0".
# Please see the LICENSE file included as part of this package.
#
# author:   Murray Altheim
# created:  2020-01-02
# modified: 2020-03-26
#
#  Arbitrator: polls the message queue for the highest priority message. 
#
#  If the new message's event is a higher priority event than that of the Action
#  currently executing, the current Action is closed and the new Action is executed.
#

import time, itertools
from threading import Thread
import datetime as dt

from lib.logger import Logger 
from lib.event import Event

# ..............................................................................
class Arbitrator(Thread):
    '''
    Arbitrates a stream of events from a MessageQueue according to 
    priority, returning to a Controller the highest priority of them.

    The Controller API is:

      .get_current_message()   returns the last message received
      .act(_current_message, _action_complete_callback)
                               act upon the current message, with
                               a callback called upon completion
    '''

    def __init__(self, config, queue, controller, level):
        super().__init__()
        Thread.__init__(self)
        self._log = Logger('arbitrator', level)
        if config is None:
            raise ValueError('no configuration provided.')
        self._config = config['ros'].get('arbitrator')
        self._idle_loop_count = 0
        self._loop_delay_sec = self._config.get('loop_delay_sec')
        self._ballistic_loop_delay_sec = self._config.get('ballistic_loop_delay_sec')
        self._queue = queue
        self._controller = controller
        self._tasks = []
        self._is_enabled = True
        self._closing = False
        self._closed = False
        self._suppressed = False
        self._counter = itertools.count()
        self._log.debug('ready.')

    # ..........................................................................
    def set_suppressed(self, suppressed):
        self._suppressed = suppressed
        self._log.info('suppressed: {}'.format(suppressed))

    # ..........................................................................
    def enable(self):
        self._log.info('enabled.')
        self._is_enabled = True

    # ..........................................................................
    def disable(self):
        self._log.info('disabled.')
        self._is_enabled = False

    # ..........................................................................
    def run(self):
        self._log.info('arbitrating tasks...')
        while self._is_enabled:
            _start_time = dt.datetime.now()
            self._loop_count = next(self._counter)
            if self._suppressed:
                # if suppressed just clear the queue so events don't build up
                self._queue.clear()
            else:
                # there are 604800 seconds in a week, 6 decimal places should do...
                self._log.debug('loop {:06d} begins with queue of {} elements.'.format(self._loop_count, self._queue.size()))
                next_messages = self._queue.next_group(5)
                if len(next_messages) == 0:
                    self._log.debug('message queue was empty.'.format(len(next_messages)))
                elif len(next_messages) == 1:
                    self._log.debug('obtained one message from queue...'.format(len(next_messages)))
                else:
                    self._log.debug('obtained {} messages from queue...'.format(len(next_messages)))
                first_message = True
                for i in range(len(next_messages)):
                    next_message = next_messages[i]
                    if first_message:
                        self._idle_loop_count = 0  # reset
                        self.accept_highest_priority_message(next_message)
                    else:
                        self._log.debug('{}: message #{:07d};\tpriority #{}: {}.'.format(i, \
                                next_message.get_number(), next_message.get_priority(), next_message.get_description()))
                    first_message = False
                # we don't care about the messages in the queue that weren't high enough priority
                self._queue.clear()
                _current_message = self._controller.get_current_message()
                if _current_message is not None:
                    if _current_message.get_event() == Event.STANDBY:
                        self._log.debug('{:06d} : current event: {}; queue: {} elements.'.format(self._loop_count, _current_message.get_event().description, self._queue.size()))
                        if (self._loop_count % 10) == 0:
                            self._log.info('{:06d} : standing by...'.format(self._loop_count))
                    else:
                        self._log.info('{:06d} : event: {}; queue: {} elements.'.format(self._loop_count, _current_message.get_event().description, self._queue.size()))
                else:  # no messages: we're idle.
                    self._idle_loop_count += 1
                    if self._idle_loop_count <= 500:
                        if (self._loop_count % 50) == 0:
                            self._log.info('{:06d} : idle.'.format(self._loop_count))
                    else:  # after being idle for a long time, dim the message
                        if (self._loop_count % 500) == 0:
                            self._log.info('{:06d} : idle...'.format(self._loop_count))
            time.sleep(self._loop_delay_sec)
            _delta = dt.datetime.now() - _start_time
            _elapsed_ms = int(_delta.total_seconds() * 1000)
            self._log.info('elapsed: {}ms'.format(_elapsed_ms))

        self._log.info('loop end.')

    # ..........................................................................
    def interrupt(self, message):
        '''
            If the current Action was not ballistic and the new one is a different Action, 
            interrupt the old Action. We can't interrupt a ballistic Action.
        '''
        _current_message = self._controller.get_current_message()
        _current_event = _current_message.get_event() if _current_message is not None else None
        # [on_true] if [expression] else [on_false] 
        _new_event = message.get_event()
        if _current_event == _new_event:
            self._log.critical('NO CHANGE in event {} (ballistic? {})...'.format(_new_event.name, _new_event.is_ballistic))
        elif _current_event.is_ballistic:
            self._log.critical('NOT INTERRUPTING current ballistic event {} (ballistic? {})...'.format(_current_event.name, _current_event.is_ballistic))
        else:
            self._log.critical('interrupting with new event {} (ballistic? {})...'.format(_new_event.name, _new_event.is_ballistic))
            message.interrupt()
            self._motors.interrupt()
        # ...

    # ..........................................................................
    def accept_highest_priority_message(self, message):
        '''
            Accepts a new message. If the contained Action is the same as the previous Action, 
            no change is warranted and we return immediately.

            If the current Action is not ballistic and the new Action is different, interrupt 
            the current Action. We don't interrupt a ballistic Action.
        '''
        if message is None:
            raise TypeError
        _number = message.get_number()
        _description = message.get_description()
        self._log.info('accept highest priority message {}; description: {}'.format(_number, _description))
        _current_message = self._controller.get_current_message()
        if _current_message is None:
            self._log.info('there is no existing message.')
        else:
            self._log.info('existing message is not None.')
            if _current_message == message:
                self._log.warning('NO CHANGE: message #{:07d};\tevent: {}; priority #{}; value: {}.'.format(\
                    message.get_number(), message.get_event().description, message.get_priority(), message.get_value()))
                return
            if not _current_message.get_event().is_ballistic:
                self._log.debug('existing action is ballistic.')
                self.interrupt(_current_message)

        _current_message = message

        self._log.info('act on message #{:07d};\tpriority #{}: {}.'.format(message.get_number(), message.get_priority(), message.get_description()))
        if _current_message.get_event().is_ballistic:
            self._log.info('acting upon accepted message with highest priority ballistic action #{}: {}'.format(message.get_number(), message.get_description()))
            self._log.info('waiting on ballistic action {}...'.format(_current_message.get_event().description))
            self._controller.act(_current_message, self._action_complete_callback)
            # then wait until completed
            while not _current_message.is_complete():
                self._log.info('loop: waiting on ballistic action {}...'.format(_current_message.get_action().description))
                time.sleep(self._ballistic_loop_delay_sec)
        else:
            self._log.info('acting upon accepted highest priority message #{}: {}'.format(message.get_number(), message.get_description()))
            self._controller.act(_current_message, self._action_complete_callback)

    # ..........................................................................
    def _action_complete_callback(self, message, current_power):
        '''
            Callback from the Controller indicating that the message/action has been completed.
            This sets the current message state to COMPLETED.
        '''
#       self._log.warning('1. event {}.'.format(message.get_event()))
#       self._log.warning('2. current power at {:>5.1f}.'.format(current_power[0]))
#       self._log.warning('3. current power at {:>5.1f}.'.format(current_power[1]))

        _current_message = self._controller.get_current_message()
        if _current_message:
            if _current_message.is_complete():
                self._log.warning('message already complete.')
                return
            elif current_power[0] is not None and current_power[1] is not None:
                self._log.info('event {} complete with current power levels at {:>5.1f}, {:>5.1f}.'.format(_current_message.get_event().name, current_power[0], current_power[1]))
            else:
                self._log.info('event {} complete with current power levels at zero.'.format(_current_message.get_event().name))
            _current_message.complete()
        else:
            self._log.critical('cannot complete callback: no current message.')

    # ..........................................................................
    def add_task(self, task):
        self._tasks.append(task)
        task.start()

    # ..........................................................................
    def close(self):
        self._is_enabled = False
        if self._closing:
            self._log.warning('already closing.')
            return
        elif self._closed:
            self._log.warning('already closed.')
            return
        self._closing = False
        if len(self._tasks) > 0:
            self._log.info('closing {} tasks...'.format(len(self._tasks)))
            for task in self._tasks:
                task.disable()
                task.close()
#               # wait for thread exit
#               task.join()
        else:
            self._log.info('no tasks to close.')
        self._closed = False
        self._log.info('closed.')

# EOF
