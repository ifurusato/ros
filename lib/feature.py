#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# Copyright 2020-2021 by Murray Altheim. All rights reserved. This file is part
# of the Robot Operating System project, released under the MIT License. Please
# see the LICENSE file included as part of this package.
#
# author:   Murray Altheim
# created:  2019-04-09
# modified: 2019-04-09
#

from abc import ABC, abstractmethod

class Feature(ABC):
    '''
        The Feature interface.
    '''
    def __init__(self, feature_name):
        super().__init__(feature_name)

    # ..........................................................................
    @abstractmethod
    def name(self) -> str:
        pass

    # ..........................................................................
    @abstractmethod
    def enable(self):
        '''
            Enable the feature.
        '''
        raise NotImplementedError

    # ..........................................................................
    @abstractmethod
    def disable(self):
        '''
            Disable the feature.
        '''
        raise NotImplementedError

#EOF
