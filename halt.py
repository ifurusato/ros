#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# Copyright 2020 by Murray Altheim. All rights reserved. This file is part of
# the Robot OS project and is released under the "Apache Licence, Version 2.0".
# Please see the LICENSE file included as part of this package.
#
# author:   Murray Altheim
# created:  2020-03-30
# modified: 2020-08-21
#
#  Quickly halts the motors if they're running.
#

import time
from lib.logger import Level
from lib.config_loader import ConfigLoader
from lib.motors import Motors

_loader = ConfigLoader(Level.INFO)
filename = 'config.yaml'
_config = _loader.configure(filename)

_motors = Motors(_config, None, None, Level.INFO)
_motors.halt()

_motors.close()

#EOF
