#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#

from colorama import init, Fore, Style
init()

from lib.logger import Logger, Level

_log = Logger("color-test", Level.INFO)

_log.info('info.')
_log.warning('warning.')
_log.error('error.')

_log.info(Fore.RED + 'RED')
_log.info(Fore.GREEN + 'GREEN')
_log.info(Fore.BLUE + 'BLUE')

_log.info(Fore.YELLOW + 'YELLOW')
_log.info(Fore.MAGENTA + 'MAGENTA')
_log.info(Fore.CYAN + 'CYAN')

_log.info(Fore.BLACK + 'BLACK')
_log.info(Fore.WHITE + 'WHITE')


