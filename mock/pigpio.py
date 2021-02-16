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

class MockPi(object):
    def __init__(self):
        pass

class MockPigpio(object):

    def __init__(self):
        self._pi = MockPi()
        pass

    def pi(self):
        return self._pi

#EOF
