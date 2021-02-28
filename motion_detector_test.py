#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# Copyright 2020 by Murray Altheim. All rights reserved. This file is part of
# the Robot OS project and is released under the "Apache Licence, Version 2.0".
# Please see the LICENSE file included as part of this package.
#
# author:   altheim
# created:  2020-03-31
# modified: 2020-03-31

import time, sys, traceback, itertools
from colorama import init, Fore, Style
init()

from lib.config_loader import ConfigLoader
from lib.event import Event
from lib.logger import Logger, Level
from lib.message_factory import MessageFactory
from lib.devnull import DevNull
from lib.motion_detector import MotionDetector

# ..............................................................................
class MockMessageBus():
    '''
    This message bus waits for one MOTION_DETECT event.
    '''
    def __init__(self, level):
        super().__init__()
        self._log = Logger("mock-queue", Level.INFO)
        self._counter = itertools.count()
        self._experienced_event = False

    # ......................................................
    def handle(self, message):
        message.number = next(self._counter)
        self._log.info('handling message #{}: priority {}: {}'.format(message.number, message.priority, message.description))
        event = message.event
        if event is Event.MOTION_DETECT:
            self._experienced_event = True
        else:
            self._log.info('other event: {}'.format(event.description))

    # ......................................................
    def is_complete(self):
        return self._experienced_event


# main .........................................................................
def main():

    _log = Logger("mot-det test", Level.INFO)

    _log.info('starting test...')
    _log.info(Fore.YELLOW + Style.BRIGHT + ' INFO  : Press Ctrl+C to exit.')
    _motion_detector = None

    try:

        _loader = ConfigLoader(Level.INFO)
        filename = 'config.yaml'
        _config = _loader.configure(filename)

        _message_factory = MessageFactory(Level.INFO)
        _message_bus = MockMessageBus(Level.INFO)
        _motion_detector = MotionDetector(_config, _message_factory, _message_bus, Level.INFO)
        _log.info('starting motion detector...')
        _motion_detector.enable()

        _counter = itertools.count()
        while not _message_bus.is_complete():
            if next(_counter) % 5 == 0:
                _log.info('waiting for motion... ')
            time.sleep(1.0)

        time.sleep(5.0)

        _motion_detector.close()
        _log.info('test complete.')

    except KeyboardInterrupt:
        if _motion_detector:
            _motion_detector.close()

    except Exception:
        _log.info(traceback.format_exc())

    finally:
        if _motion_detector:
            _motion_detector.close()

if __name__== "__main__":
    main()

#EOF
