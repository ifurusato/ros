#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# author:   Murray Altheim
# created:  2021-02-18
# modified: 2021-02-23
#
# Provides a typical user-confirmation function.
#

from colorama import init, Fore, Style
init()

def confirm(default=True):
    _answer = input(Fore.YELLOW + '\nDo you want to continue? {} '.format(\
            '[Y/n]' if default else '[y/N]') + Style.RESET_ALL).lower()
    if len(_answer) == 0: # user typed 'Return'
        return default
    else: 
        return _answer in ['yes', 'y']

#EOF
