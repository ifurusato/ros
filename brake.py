#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# Copyright 2020 by Murray Altheim. All rights reserved. This file is part of
# the Robot OS project and is released under the "Apache Licence, Version 2.0".
# Please see the LICENSE file included as part of this package.
#

from colorama import init, Fore, Style
init()

from lib.logger import Level
from lib.motors import Motors
from lib.config_loader import ConfigLoader

# ..............................................................................
try:

    print('brake             :' + Fore.CYAN + Style.BRIGHT + ' INFO  : braking...' + Style.RESET_ALL)

    # read YAML configuration
    _loader = ConfigLoader(Level.INFO)
    filename = 'config.yaml'
    _config = _loader.configure(filename)

    _motors = Motors(_config, None, Level.INFO)
    _motors.brake()

except KeyboardInterrupt:
    print(Fore.RED + 'Ctrl-C caught in main: exiting...' + Style.RESET_ALL)
finally:
    _motors.stop()
    _motors.close()
    print('brake             :' + Fore.CYAN + Style.BRIGHT + ' INFO  : complete.' + Style.RESET_ALL)

#EOF
