#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# Copyright 2020 by Murray Altheim. All rights reserved. This file is part of
# the Robot OS project and is released under the "Apache Licence, Version 2.0".
# Please see the LICENSE file included as part of this package.
#
# author:   Murray Altheim
# created:  2020-12-20
# modified: 2020-12-20
#
# Prints the Raspberry Pi temperature to the console.
#

from colorama import init, Fore, Style
init()

from lib.logger import Logger, Level

# ..............................................................................

_log = Logger("cpu-temp", Level.INFO)

try:

    _file = '/sys/class/thermal/thermal_zone0/temp'
    f=open(_file, "r")
    if f.mode == 'r':
        contents = int(f.read())
        _log.info('CPU temperature: {:5.2f}°C'.format(contents/1000.0))
    else:
        _log.info(Fore.RED + 'unable to obtain CPU temperature.' + Style.RESET_ALL)

except KeyboardInterrupt:
    _log.info('Ctrl-C caught: complete.' )
except Exception as e:
    _log.error('error closing: {}'.format(e))


#EOF
