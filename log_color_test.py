#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# Copyright 2020-2021 by Murray Altheim. All rights reserved. This file is part
# of the Robot Operating System project, released under the MIT License. Please
# see the LICENSE file included as part of this package.
#

from colorama import init, Fore, Style
init()

from lib.logger import Logger, Level

_log = Logger("color-test", Level.DEBUG)

_log.debug('debug.')
_log.info('info.')
_log.notice('notice.')
_log.warning('warning.')
_log.error('error.')
_log.critical('critical.')
_log.heading('title', 'message.', 'info [0/0]')

_log.info(Fore.RED + 'RED')
_log.info(Fore.GREEN + 'GREEN')
_log.info(Fore.BLUE + 'BLUE')

_log.info(Fore.YELLOW + 'YELLOW')
_log.info(Fore.MAGENTA + 'MAGENTA')
_log.info(Fore.CYAN + 'CYAN')

_log.info(Fore.BLACK + 'BLACK')
_log.info(Fore.WHITE + 'WHITE')


