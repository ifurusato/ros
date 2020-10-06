#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# Copyright 2020 by Murray Altheim. All rights reserved. This file is part of
# the Robot OS project and is released under the "Apache Licence, Version 2.0".
# Please see the LICENSE file included as part of this package.
#

import logging, traceback, threading
from logging.handlers import RotatingFileHandler
from datetime import datetime as dt
from enum import Enum
from colorama import init, Fore, Style
init()

class Level(Enum):
    DEBUG    = logging.DEBUG     # 10
    INFO     = logging.INFO      # 20
    WARN     = logging.WARN      # 30
    ERROR    = logging.ERROR     # 40
    CRITICAL = logging.CRITICAL  # 50

# ..............................................................................
class Logger:

    _suppress = False

    def __init__(self, name, level, log_to_file=False):
        '''
           Writes to a named log with the provided level, defaulting to a
           console (stream) handler unless 'log_to_file' is True, in which
           case only write to file, not to the console.
        '''
        # create logger
        self.__log = logging.getLogger(name)
        self.__log.propagate = False
        self._name = name
        self._level = level
        self.__log.setLevel(self._level.value)
        self._mutex = threading.Lock()
        # some of this could be set via configuration
        self._include_timestamp = True 
#       self._date_format = '%Y-%m-%d %H:%M:%S'
        self._date_format = '%H:%M:%S'
        if not self.__log.handlers: # log to stream ............................
            if log_to_file:
                _ts = dt.utcfromtimestamp(dt.utcnow().timestamp()).isoformat().replace(':','_').replace('-','_').replace('.','_')
                _filename = './log/ros-{}.csv'.format(_ts)
                self.info("logging to file: {}".format(_filename))
                fh = RotatingFileHandler(filename=_filename, mode='w', maxBytes=262144, backupCount=10)
                fh.setLevel(level.value)
                if self._include_timestamp:
                    fh.setFormatter(logging.Formatter('%(asctime)s.%(msecs)06f\t|%(name)s|%(message)s', datefmt=self._date_format))
                else:
                    fh.setFormatter(logging.Formatter('%(name)s|%(message)s'))
                self.__log.addHandler(fh)
            else: # log to console .............................................
                sh = logging.StreamHandler()
                sh.setLevel(level.value)
                if self._include_timestamp:
                    sh.setFormatter(logging.Formatter(Fore.BLACK + '%(asctime)s.%(msecs)06f :' + Fore.RESET + '\t%(name)s ' + ( ' '*(16-len(name)) ) + ' : %(message)s', datefmt=self._date_format))
#                   sh.setFormatter(logging.Formatter('%(asctime)s.%(msecs)06f  %(name)s ' + ( ' '*(16-len(name)) ) + ' : %(message)s', datefmt=self._date_format))
                else:
                    sh.setFormatter(logging.Formatter('%(name)s ' + ( ' '*(16-len(name)) ) + ' : %(message)s'))
                self.__log.addHandler(sh)

    # ..........................................................................
    def set_suppress(self, suppress):
        '''
           If set True, suppresses all log messages except critical errors
           and log-to-file messages. This is global across all Loggers.
        '''
        type(self)._suppress = suppress

    @property
    def suppressed(self):
        return type(self)._suppress

    # ..........................................................................
    def get_mutex(self):
        return self._mutex

    # ..........................................................................
    def set_mutex(self, mutex):
        self._mutex = mutex

    # ..........................................................................
    def debug(self, message):
        if not self.suppressed:
            with self._mutex:
                self.__log.debug(Fore.BLACK + "DEBUG : " + message + Style.RESET_ALL)

    # ..........................................................................
    def info(self, message):
        if not self.suppressed:
            with self._mutex:
                self.__log.info(Fore.CYAN + "INFO  : " + message + Style.RESET_ALL)

    # ..........................................................................
    def warning(self, message):
        if not self.suppressed:
            with self._mutex:
                self.__log.warning(Fore.YELLOW + "WARN  : " + message + Style.RESET_ALL)

    # ..........................................................................
    def error(self, message):
        if not self.suppressed:
            with self._mutex:
                self.__log.error(Fore.RED + Style.NORMAL + "ERROR : " + Style.BRIGHT + message + Style.RESET_ALL)

    # ..........................................................................
    def critical(self, message):
        with self._mutex:
            self.__log.critical(Fore.WHITE + "FATAL : " + Style.BRIGHT + message + Style.RESET_ALL)

    # ..........................................................................
    def file(self, message):
        '''
           This is just info() but without any formatting.
        '''
        with self._mutex:
            self.__log.info(message)

#EOF
