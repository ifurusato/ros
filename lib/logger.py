#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# Copyright 2020 by Murray Altheim. All rights reserved. This file is part of
# the Robot OS project and is released under the "Apache Licence, Version 2.0".
# Please see the LICENSE file included as part of this package.
#

import logging, traceback, threading
from enum import Enum
from colorama import init, Fore, Style
init()

class Level(Enum):
    DEBUG    = logging.DEBUG     # 10
    INFO     = logging.INFO      # 20
    WARN     = logging.WARN      # 30
    ERROR    = logging.ERROR     # 40
    CRITICAL = logging.CRITICAL  # 50


class Logger:

    def __init__(self, name, level):

        # create logger
        self.__log = logging.getLogger(name)
        self.__log.propagate = False
        self._mutex = threading.Lock()
        if not self.__log.handlers:
            self.__log.setLevel(level.value)
            # create console handler and set level
            sh = logging.StreamHandler()
            sh.setLevel(level.value)
            # create formatter
            sh.setFormatter(logging.Formatter('%(name)s ' + ( ' '*(16-len(name)) ) + ' : %(message)s'))
            self.__log.addHandler(sh)

    def debug(self,message):
        with self._mutex:
            self.__log.debug(Fore.BLACK + "DEBUG : " + message + Style.RESET_ALL)

    def info(self,message):
        with self._mutex:
            self.__log.info(Fore.CYAN + "INFO  : " + message + Style.RESET_ALL)

    def warning(self,message):
        with self._mutex:
            self.__log.warning(Fore.YELLOW + "WARN  : " + message + Style.RESET_ALL)

    def error(self,message):
        with self._mutex:
            self.__log.error(Fore.RED + Style.NORMAL + "ERROR : " + Style.BRIGHT + message + Style.RESET_ALL)

    def critical(self,message):
        with self._mutex:
            self.__log.critical(Fore.WHITE + "FATAL : " + Style.BRIGHT + message + Style.RESET_ALL)

#EOF
