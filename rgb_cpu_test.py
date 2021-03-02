#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# Copyright 2020-2021 by Murray Altheim. All rights reserved. This file is part
# of the Robot Operating System project, released under the MIT License. Please
# see the LICENSE file included as part of this package.
#
# author:   Murray Altheim
# created:  2021-02-09
# modified: 2021-02-09
#

import sys, time
from colorama import init, Fore, Style
init()

from lib.rgbmatrix import RgbMatrix, Color, DisplayType
from lib.logger import Level

# main .........................................................................


def main():
    print(Fore.GREEN + 'main begin.  ......................................................... ' + Style.RESET_ALL)

    print('rgbmatrix_test    :' + Fore.CYAN + Style.BRIGHT + ' INFO  : starting test...' + Style.RESET_ALL)
    _rgbmatrix = None

    try:

        _rgbmatrix = RgbMatrix(Level.WARN)
        _rgbmatrix.set_display_type(DisplayType.CPU)
        _rgbmatrix.enable()
        while True:
            time.sleep(1.0)

    except KeyboardInterrupt:
        print('rgbmatrix_test    :' + Fore.YELLOW + ' INFO  : Ctrl-C caught: exiting...' + Style.RESET_ALL)
    finally:
        if _rgbmatrix is not None:
            _rgbmatrix.set_color(Color.BLACK)
            _rgbmatrix.disable()
            _rgbmatrix.close()

if __name__== "__main__":
    main()

#EOF
