#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# Copyright 2021 by Murray Altheim. All rights reserved. This file is part of
# the Robot OS project and is released under the "Apache Licence, Version 2.0".
# Please see the LICENSE file included as part of this package.
#
# author:   Murray Altheim
# created:  2021-02-25
# modified: 2021-02-25
#
# Just manually turns the cooling fan off.
#

import sys
from lib.fan import Fan
from lib.logger import Level
from lib.config_loader import ConfigLoader

try:

    # read YAML configuration
    _loader = ConfigLoader(Level.INFO)
    filename = 'config.yaml'
    _config = _loader.configure(filename)

    fan = Fan(_config, Level.INFO)
    fan.disable()

except Exception as e:
    print('error turning fan off: {}'.format(e))
    sys.exit(1)

