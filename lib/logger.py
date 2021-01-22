#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# Copyright 2020 by Murray Altheim. All rights reserved. This file is part of
# the Robot OS project and is released under the "Apache Licence, Version 2.0".
# Please see the LICENSE file included as part of this package.
#

import logging, math, traceback, threading
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
#       _format='%(asctime)s.%(msecs)03d %(levelname)s {%(module)s} [%(funcName)s] %(message)s', 
        self._date_format='%Y-%m-%dT%H:%M:%S'
#       self._date_format = '%Y-%m-%dT%H:%M:%S.%f'
#       self._date_format = '%H:%M:%S'
        if not self.__log.handlers: # log to stream ............................
            if log_to_file:
                _ts = dt.utcfromtimestamp(dt.utcnow().timestamp()).isoformat().replace(':','_').replace('-','_').replace('.','_')
                _filename = './log/ros-{}.csv'.format(_ts)
                self.info("logging to file: {}".format(_filename))
                fh = RotatingFileHandler(filename=_filename, mode='w', maxBytes=262144, backupCount=10)
                fh.setLevel(level.value)
                if self._include_timestamp:
                    fh.setFormatter(logging.Formatter('%(asctime)s.%(msecs)03dZ\t|%(name)s|%(message)s', datefmt=self._date_format))
                else:
                    fh.setFormatter(logging.Formatter('%(name)s|%(message)s'))
                self.__log.addHandler(fh)
            else: # log to console .............................................
                sh = logging.StreamHandler()
                sh.setLevel(level.value)
                if self._include_timestamp:
                    sh.setFormatter(logging.Formatter(Fore.BLACK + '%(asctime)s.%(msecs)3fZ\t:' \
                            + Fore.RESET + ' %(name)s ' + ( ' '*(16-len(name)) ) + ' : %(message)s', datefmt=self._date_format))
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
    def level(self):
        return self._level

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

    # headings .................................................................

    def header(self, title, message, info):
        '''
           Print a formatted, titled message to info(), inspired by maven console messaging.

           :param title:    the required title of the heading.
           :param message:  the optional message to display; if None only the title will be displayed.
           :param info:     an optional second message to display right-justified; ignored if None.
        '''
        MAX_WIDTH = 80
        MARGIN = 27
        if title is None or len(title) == 0:
            raise ValueError('no title parameter provided (required)')
        _available_width = MAX_WIDTH - MARGIN
        self.info(self._get_title_bar(title, _available_width))
        if message:
            if info is None:
                info = ''
            _min_msg_width = len(message) + 1 + len(info)
            if _min_msg_width >= _available_width:
                # if total length is greater than available width, just print
                self.info(Fore.WHITE + Style.BRIGHT + '{} {}'.format(message, info))
            else:
                _message_2_right = info.rjust(_available_width - len(message) - 2)
                self.info(Fore.WHITE + Style.BRIGHT + '{} {}'.format(message, _message_2_right))
            # print footer
            self.info(Fore.WHITE + Style.BRIGHT + Logger._repeat('-', _available_width-1))
        # print spacer
        self.info('')

    def _get_title_bar(self, message, MAX_WIDTH):
        _carrier_width = len(message) + 4
        _hyphen_width = math.floor( ( MAX_WIDTH - _carrier_width ) / 2 )
        if _hyphen_width <= 0:
            return message
        elif len(message) % 2 == 0: # message is even length
            return Fore.WHITE + Style.BRIGHT + Logger._repeat('-', _hyphen_width) + '< ' + Fore.CYAN + Style.NORMAL\
                    + message + Fore.WHITE + Style.BRIGHT + ' >' + Logger._repeat('-', _hyphen_width)
        else:
            return Fore.WHITE + Style.BRIGHT + Logger._repeat('-', _hyphen_width) + '< ' + Fore.CYAN + Style.NORMAL\
                    + message + Fore.WHITE + Style.BRIGHT + ' >' + Logger._repeat('-', _hyphen_width-1)

    @staticmethod
    def _repeat(s, wanted):
        return (s * (wanted//len(s) + 1))[:wanted]

#EOF
