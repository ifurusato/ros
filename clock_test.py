#!/usr/bin/env python3.7
# -*- coding: utf-8 -*-
#
# Copyright 2020 by Murray Altheim. All rights reserved. This file is part
# of the pimaster2ardslave project and is released under the MIT Licence;
# please see the LICENSE file included as part of this package.
#
# author:   Murray Altheim
# created:  2020-10-27
# modified: 2020-10-27
#

import time, itertools, traceback
from datetime import datetime as dt
from colorama import init, Fore, Style
init()

from lib.logger import Logger, Level
from lib.config_loader import ConfigLoader
from lib.event import Event
from lib.message import MessageFactory
from lib.queue import MessageQueue
from lib.clock import Clock


# ..............................................................................
class MockMessageQueue():
    '''
        This message queue just displays filtered, clock-related events as they arrive.
    '''
    def __init__(self, level):
        super().__init__()
        self._counter = itertools.count()
        self._log = Logger("queue", Level.INFO)
        self._start_time = dt.now()
        self._log.info('ready.')

    # ......................................................
    def add(self, message):
        message.number = next(self._counter)
        self._log.debug('added message {:06d}: priority {}: {}'.format(message.number, message.priority, message.description))
        _event = message.event
        _value = message.value

        _delta = dt.now() - self._start_time
        _elapsed_ms = _delta.total_seconds() * 1000
        _process_delta = dt.now() - message.timestamp
        _process_ms = _process_delta.total_seconds() * 1000
        _total_ms = _elapsed_ms + _process_ms

        if _event is Event.CLOCK_TICK:
            self._log.info(Fore.YELLOW + Style.NORMAL + 'CLOCK_TICK: {}; value: {}'.format(_event.description, _value))

        elif _event is Event.CLOCK_TOCK:
            self._log.info(Fore.GREEN + Style.NORMAL + 'event: {}; value: {}; processing time: {:6.3f}ms; loop: {:6.3f}ms elapsed; total: {:6.3f}ms'.format(\
                    _event.description, _value, _process_ms, _elapsed_ms, _total_ms))
            self._start_time = dt.now()
        else:
            self._log.info(Fore.BLACK + Style.BRIGHT + 'other event: {}'.format(_event.description))

# ..............................................................................
def main():

    try:

        _loader = ConfigLoader(Level.INFO)
        filename = 'config.yaml'
        _config = _loader.configure(filename)

        _message_factory = MessageFactory(Level.INFO)
#       _queue = MessageQueue(_message_factory, Level.INFO)
        _queue = MockMessageQueue(Level.INFO)
        _clock = Clock(_config, _queue, _message_factory, Level.INFO)

        _clock.enable()

        while True:
            time.sleep(1.0)

    except KeyboardInterrupt:
        print(Fore.RED + 'Ctrl-C caught; exiting...' + Style.RESET_ALL)
    except Exception as e:
        print(Fore.RED + Style.BRIGHT + 'error starting ifs: {}\n{}'.format(e, traceback.format_exc()) + Style.RESET_ALL)
    finally:
        pass


if __name__== "__main__":
    main()

#EOF


