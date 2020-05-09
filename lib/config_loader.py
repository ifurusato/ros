#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# Copyright 2020 by Murray Altheim. All rights reserved. This file is part of
# the Robot Operating System project and is released under the "Apache Licence, 
# Version 2.0". Please see the LICENSE file included as part of this package.
#
# author:   Murray Altheim
# created:  2020-04-15
# modified: 2020-04-15

import yaml

from lib.logger import Level, Logger

class ConfigLoader():
    '''
        Has just one method: configure() reads a YAML file.
    '''
    def __init__(self, level):
        self._log = Logger('configloader', level)
        self._log.info('ready.')

    # ..........................................................................
    def configure(self, filename):
        '''
            Read and return configuration from the specified YAML file.
        '''
        self._log.info('reading from yaml configuration file {}...'.format(filename))
        _config = yaml.safe_load(open(filename, 'r'))
        for key, value in _config.items():
            self._log.debug('config key: {}; value: {}'.format(key, str(value)))
        self._log.info('configuration read.')
        return _config

#EOF
