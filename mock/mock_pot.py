#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# Copyright 2020 by Murray Altheim. All rights reserved. This file is part of
# the Robot Operating System project and is released under the "Apache Licence,
# Version 2.0". Please see the LICENSE file included as part of this package.
#
# author:   Murray Altheim
# created:  2021-02-12
# modified: 2021-02-12
#

# ...............................................................
class MockPotentiometer(object):
    '''
    For testing, or when we don't have an RGB LED Potentiometer attached.
    '''
    def __init__(self):
        self._min_pot = 0.0
        self._max_pot = 0.0
        self._value   = 0.0
        self._step    = 0.0

    def set_output_limits(self, min_pot, max_pot):
        self._min_pot = min_pot
        self._max_pot = max_pot
        self._step    = max_pot / 20.0

    def get_scaled_value(self, update_led=True):
        if self._value < self._max_pot:
            self._value += self._step
        else:
            self._value = self._min_pot
        return self._value

#EOF
