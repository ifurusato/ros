#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# Copyright 2020-2021 by Murray Altheim. All rights reserved. This file is part
# of the Robot Operating System project, released under the MIT License. Please
# see the LICENSE file included as part of this package.
#
# author:   Murray Altheim
# created:  2020-01-19
#

class DevNull(object):
    '''
        A sink for error messages.
    '''
    def __init__(self):
        pass

    def write(self, msg):
        pass

