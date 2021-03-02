#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# Copyright 2020-2021 by Murray Altheim. All rights reserved. This file is part
# of the Robot Operating System project, released under the MIT License. Please
# see the LICENSE file included as part of this package.
#
# author:   Murray Altheim
# created:  2021-02-18
# modified: 2021-02-23
#
# Provides a typical user-confirmation function.
#

def confirm(default=True):
    _answer = input('\nDo you want to continue? {} '.format('[Y/n]' if default else '[y/N]')).lower()
    if len(_answer) == 0: # user typed 'Return'
        return default
    else: 
        return _answer in ['yes', 'y']

#EOF
