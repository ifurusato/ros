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

# Import library functions we need
import time, sys, traceback, itertools
from colorama import init, Fore, Style
init()

from lib.i2c_scanner import I2CScanner
from lib.config_loader import ConfigLoader
from lib.event import Event
from lib.logger import Logger, Level
from lib.devnull import DevNull
from lib.catscan import CatScan


# ..............................................................................
class MockMessageQueue():
    '''
        This message queue waits for one CAT_SCAN event.
    '''
    def __init__(self, level):
        super().__init__()
        self._log = Logger("mock-queue", Level.INFO)
        self._counter = itertools.count()
        self._experienced_event = False

    # ......................................................
    def add(self, message):
        message.set_number(next(self._counter))
        self._log.info('added message #{}: priority {}: {}'.format(message.get_number(), message.get_priority(), message.get_description()))
        event = message.get_event()
        if event is Event.CAT_SCAN:
            self._experienced_event = True
        else:
            self._log.info('other event: {}'.format(event.description))

    # ......................................................
    def is_complete(self):
        return self._experienced_event


# main .........................................................................
def main():

    _log = Logger("cat-scan test", Level.INFO)

    _log.info('starting test...')
    _log.info(Fore.YELLOW + Style.BRIGHT + ' INFO  : Press Ctrl+C to exit.')

    try:

        _i2c_scanner = I2CScanner(Level.WARN)
        _addresses = _i2c_scanner.getAddresses()
        hexAddresses = _i2c_scanner.getHexAddresses()
        _addrDict = dict(list(map(lambda x, y:(x,y), _addresses, hexAddresses)))
        for i in range(len(_addresses)):
            _log.debug(Fore.BLACK + Style.DIM + 'found device at address: {}'.format(hexAddresses[i]) + Style.RESET_ALL)
        ultraborg_available = ( 0x36 in _addresses )
    
        if not ultraborg_available:
            raise OSError('UltraBorg hardware dependency not available.')

        _log.info('starting cat scan...')

        _loader = ConfigLoader(Level.INFO)
        filename = 'config.yaml'
        _config = _loader.configure(filename)

        _queue = MockMessageQueue(Level.INFO)
        _catscan = CatScan(_config, _queue, Level.INFO)
        _catscan.enable()

        _catscan.set_mode(True)

        _count = 0
        while not _queue.is_complete():
            if _count % 5 == 0:
                _log.info('waiting for cat... ' + Fore.BLACK + Style.DIM + '({:d} sec)'.format(_count))
            time.sleep(1.0)
            _count += 1

        time.sleep(3.0)

        _catscan.close()
        _log.info('test complete.')

    except KeyboardInterrupt:
        if _catscan:
            _catscan.close()

    except Exception:
        _log.info(traceback.format_exc())

    finally:
        if _catscan:
            _catscan.close()

if __name__== "__main__":
    main()

#EOF
