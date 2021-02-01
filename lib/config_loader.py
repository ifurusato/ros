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

import pprint
from colorama import init, Fore, Style
init()
try:
    import yaml
except ImportError:
    exit("This script requires the pyyaml module\nInstall with: sudo pip3 install pyyaml")

from lib.logger import Level, Logger

class ConfigLoader():
    '''
        Has just one method: configure() reads a YAML file.
    '''
    def __init__(self, level):
        self._log = Logger('configloader', level)
        self._log.info('ready.')

    # ..........................................................................
    def configure(self, filename='config.yaml'):
        '''
        Read and return configuration from the specified YAML file.

        Pretty-prints the configuration object if the log level is set to DEBUG.
        '''
        self._log.info('reading from yaml configuration file {}...'.format(filename))
        _config = yaml.safe_load(open(filename, 'r'))
        if self._log.level == Level.DEBUG:
            self._log.debug('YAML configuration as read:')
            print(Fore.BLUE)
            pp = pprint.PrettyPrinter(width=80, indent=2)
            pp.pprint(_config)
            print(Style.RESET_ALL)
        self._log.info('configuration read.')
        return _config

#EOF
