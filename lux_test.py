#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# Copyright 2020 by Murray Altheim. All rights reserved. This file is part of
# the Robot Operating System project and is released under the "Apache Licence, 
# Version 2.0". Please see the LICENSE file included as part of this package.
#
# author:   Murray Altheim
# created:  2020-08-20
# modified: 2020-08-20
#

import time 
from colorama import init, Fore, Style
init()

from lib.lux import Lux
from lib.logger import Level

# ..............................................................................
def main():

    try:

        _lux = Lux(Level.INFO)

        while True:
            _value = _lux.get_value()
            if _value < 10.0:
                _color = Fore.BLUE
            elif _value < 50.0:
                _color = Fore.GREEN
            elif _value < 100.0:
                _color = Fore.YELLOW
            elif _value < 500.0:
                _color = Fore.RED
            else:
                _color = Fore.MAGENTA
            print(Fore.BLACK + 'lux: ' + _color + ' value={:06.2f}'.format(_value) + Style.RESET_ALL)
            time.sleep(1.0)

    except KeyboardInterrupt:
        print(Fore.RED + 'Ctrl-C caught; exiting...' + Style.RESET_ALL)

if __name__== "__main__":
    main()

#EOF
