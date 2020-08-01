#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# Copyright 2020 by Murray Altheim. All rights reserved. This file is part
# of the pimaster2ardslave project and is released under the MIT Licence;
# please see the LICENSE file included as part of this package.
#
# author:   Murray Altheim
# created:  2020-06-13
# modified: 2020-06-13
#

from enum import Enum

class PinType(Enum):
    '''
        Enumerates the various available microcontroller pin types. 
        The alias value may be used in the YAML configuration file.

    name                      n  description             alias
    '''
    # system events ....................
    DIGITAL_INPUT         = ( 0, 'digital input',        'DIN' )
    DIGITAL_INPUT_PULLUP  = ( 1, 'digital input pullup', 'DNP' )
    ANALOG_INPUT          = ( 2, 'analog input',         'AIN' )
    OUTPUT                = ( 3, 'output',               'OUT' )
    UNUSED                = ( 4, 'unused',               'UND' )

    # ..................................
    def __new__(cls, *args, **kwds):
        obj = object.__new__(cls)
        obj._value_ = args[0]
        return obj

    # ignore the first param since it's already set by __new__
    def __init__(self, num, description, alias):
        self._description = description
        self._alias = alias

    # this makes sure the description is read-only
    @property
    def description(self):
        return self._description

    # this makes sure the alias is read-only
    @property
    def alias(self):
        return self._alias

    # the normal value returned for an enum
    def __str__(self):
        return self.name

    @staticmethod
    def from_str(label):
        '''
            Matches the name or alias.
        '''
        if label.upper() == 'DIGITAL_INPUT_PULLUP' or label.upper() == 'DNP':
            return PinType.DIGITAL_INPUT_PULLUP
        elif label.upper() == 'DIGITAL_INPUT' or label.upper() == 'DIN':
            return PinType.DIGITAL_INPUT
        elif label.upper() == 'ANALOG_INPUT' or label.upper() == 'AIN':
            return PinType.ANALOG_INPUT
        elif label.upper() == 'OUTPUT' or label.upper() == 'OUT':
            return PinType.OUTPUT
        else:
            raise NotImplementedError

#EOF
