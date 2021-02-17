#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# Copyright 2020 by Murray Altheim. All rights reserved. This file is part of
# the Robot OS project and is released under the "Apache Licence, Version 2.0".
# Please see the LICENSE file included as part of this package.
#
# author:   Murray Altheim
# created:  2021-02-11
# modified: 2021-02-11
#
# A very limited mock pigpio stack.
#

class _callbackThread(object):
    def __init__(self):
        self.name = '_callback'

class MockPi(object):
    def __init__(self):
        self._notify = _callbackThread()

    def get_pigpio_version(self):
        return 'mock'

    def set_mode(self, pin, mode):
        pass

    def set_pull_up_down(self, pin, mode):
        pass

    def stop(self):
        pass

    def callback(self, pin, edge, func):
        pass

# GPIO edges

RISING_EDGE  = 0
FALLING_EDGE = 1
EITHER_EDGE  = 2

# GPIO modes

INPUT  = 0
OUTPUT = 1
ALT0   = 4
ALT1   = 5
ALT2   = 6
ALT3   = 7
ALT4   = 3
ALT5   = 2

# GPIO Pull Up Down

PUD_OFF  = 0
PUD_DOWN = 1
PUD_UP   = 2

class MockPigpio(object):

    def __init__(self):
        self._pi = MockPi()
        pass

    def pi(self):
        return self._pi

#EOF
