#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# Copyright 2020-2021 by Murray Altheim. All rights reserved. This file is part
# of the Robot Operating System project, released under the MIT License. Please
# see the LICENSE file included as part of this package.
#
# author:   Murray Altheim
# created:  2020-01-14
# modified: 2021-01-28
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

    @staticmethod
    def from_str(label):
        if label.upper()   == 'DEBUG':
            return Level.DEBUG
        elif label.upper() == 'INFO':
            return Level.INFO
        elif label.upper() == 'WARN':
            return Level.WARN
        elif label.upper() == 'ERROR':
            return Level.ERROR
        elif label.upper() == 'CRITICAL':
            return Level.CRITICAL
        else:
            raise NotImplementedError

# ..............................................................................
class Logger:

    _suppress = False
    __color_debug    = Fore.BLUE   + Style.DIM
    __color_info     = Fore.CYAN   + Style.NORMAL
    __color_notice   = Fore.CYAN   + Style.BRIGHT
    __color_warning  = Fore.YELLOW + Style.NORMAL
    __color_error    = Fore.RED    + Style.NORMAL
    __color_critical = Fore.WHITE  + Style.NORMAL
    __color_reset    = Style.RESET_ALL

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
        self._fh = None # optional file handler
        self._sh = None # optional stream handler

        # i18n?
        self.__DEBUG_TOKEN = 'DEBUG'
        self.__INFO_TOKEN  = 'INFO '
        self.__WARN_TOKEN  = 'WARN '
        self.__ERROR_TOKEN = 'ERROR'
        self.__FATAL_TOKEN = 'FATAL'
        self._mf = '{}{} : {}{}'
        self.mutex = threading.Lock()
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
                self._fh = RotatingFileHandler(filename=_filename, mode='w', maxBytes=262144, backupCount=10)
#               self._fh.setLevel(level.value)
                if self._include_timestamp:
                    self._fh.setFormatter(logging.Formatter('%(asctime)s.%(msecs)03dZ\t|%(name)s|%(message)s', datefmt=self._date_format))
                else:
                    self._fh.setFormatter(logging.Formatter('%(name)s|%(message)s'))
                self.__log.addHandler(self._fh)
            else: # log to console .............................................
                self._sh = logging.StreamHandler()
#               self._sh.setLevel(level.value)
                if self._include_timestamp:
                    self._sh.setFormatter(logging.Formatter(Fore.BLUE + Style.DIM + '%(asctime)s.%(msecs)3fZ\t:' \
                            + Fore.RESET + ' %(name)s ' + ( ' '*(16-len(name)) ) + ' : %(message)s', datefmt=self._date_format))
#                   self._sh.setFormatter(logging.Formatter('%(asctime)s.%(msecs)06f  %(name)s ' + ( ' '*(16-len(name)) ) + ' : %(message)s', datefmt=self._date_format))
                else:
                    self._sh.setFormatter(logging.Formatter('%(name)s ' + ( ' '*(16-len(name)) ) + ' : %(message)s'))
                self.__log.addHandler(self._sh)
        self.level = level

    # ..........................................................................
    def set_suppress(self, suppress):
        '''
           If set True, suppresses all log messages except critical errors
           and log-to-file messages. This is global across all Loggers.
        '''
        type(self)._suppress = suppress

    # ..........................................................................
    @property
    def level(self):
        return self._level

    # ..........................................................................
    @level.setter
    def level(self, level):
        self._level = level
        self.__log.setLevel(self._level.value)
        if self._fh:
            self._fh.setLevel(level.value)
        if self._sh:
            self._sh.setLevel(level.value)

    # ..........................................................................
    @property
    def suppressed(self):
        return type(self)._suppress

    # ..........................................................................
    @property
    def mutex(self):
        return self._mutex

    # ..........................................................................
    @mutex.setter
    def mutex(self, mutex):
        self._mutex = mutex

    # ..........................................................................
    def debug(self, message):
        '''
        Prints a debug message.

        The optional 'end' argument is for special circumstances where a different end-of-line is desired.
        '''
        if not self.suppressed:
            with self._mutex:
                self.__log.debug(self._mf.format(Logger.__color_debug, self.__DEBUG_TOKEN, message, Logger.__color_reset))

    # ..........................................................................
    def info(self, message):
        '''
        Prints an informational message.

        The optional 'end' argument is for special circumstances where a different end-of-line is desired.
        '''
        if not self.suppressed:
            with self._mutex:
                self.__log.info(self._mf.format(Logger.__color_info, self.__INFO_TOKEN, message, Logger.__color_reset))

    # ..........................................................................
    def notice(self, message):
        '''
        Functionally identical to info() except it prints the message brighter.

        The optional 'end' argument is for special circumstances where a different end-of-line is desired.
        '''
        if not self.suppressed:
            with self._mutex:
                self.__log.info(self._mf.format(Logger.__color_notice, self.__INFO_TOKEN, message, Logger.__color_reset))

    # ..........................................................................
    def warning(self, message):
        '''
        Prints a warning message.

        The optional 'end' argument is for special circumstances where a different end-of-line is desired.
        '''
        if not self.suppressed:
            with self._mutex:
                self.__log.warning(self._mf.format(Logger.__color_warning, self.__WARN_TOKEN, message, Logger.__color_reset))

    # ..........................................................................
    def error(self, message):
        '''
        Prints an error message.

        The optional 'end' argument is for special circumstances where a different end-of-line is desired.
        '''
        if not self.suppressed:
            with self._mutex:
                self.__log.error(self._mf.format(Logger.__color_error, self.__ERROR_TOKEN, Style.NORMAL + message, Logger.__color_reset))

    # ..........................................................................
    def critical(self, message):
        '''
        Prints a critical or otherwise application-fatal message.
        '''
        with self._mutex:
            self.__log.critical(self._mf.format(Logger.__color_critical, self.__FATAL_TOKEN, Style.BRIGHT + message, Logger.__color_reset))

    # ..........................................................................
    def file(self, message):
        '''
           This is just info() but without any formatting.
        '''
        with self._mutex:
            self.__log.info(message)

    # headings .................................................................

    def heading(self, title, message, info):
        '''
           Print a formatted, titled message to info(), inspired by maven console messaging.

           :param title:    the required title of the heading.
           :param message:  the optional message to display; if None only the title will be displayed.
           :param info:     an optional second message to display right-justified; ignored if None.
        '''
        MAX_WIDTH = 100
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
