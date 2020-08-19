#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# Copyright 2020 by Murray Altheim. All rights reserved. This file is part of
# the Robot OS project and is released under the "Apache Licence, Version 2.0".
# Please see the LICENSE file included as part of this package.
#
#  Tests the 'sworl' type on a pair of RgbMatrix5x5 displays. This is
#  currently a work-in-progress.
#

import sys, time
from colorama import init, Fore, Style
init()

from lib.rgbmatrix import RgbMatrix, Color, DisplayType
from lib.logger import Level

# main .........................................................................

def main():
    print(Fore.GREEN + 'main begin.  ......................................................... ' + Style.RESET_ALL)

    print('rgb_sworl_test    :' + Fore.CYAN + Style.BRIGHT + ' INFO  : starting test...' + Style.RESET_ALL)

    try:

        _rgbmatrix = RgbMatrix(Level.INFO)

        display_type = DisplayType.SWORL
        print('rgb_sworl_test    :' + Fore.CYAN + Style.BRIGHT + ' INFO  : displaying {}...'.format(display_type.name) + Style.RESET_ALL)
        _rgbmatrix.set_display_type(display_type)
        _rgbmatrix.enable()
        time.sleep(2.0)
        _rgbmatrix.disable()

        count = 0
        while not _rgbmatrix.is_disabled():
            count += 1
            time.sleep(1.0)
            if count > 5:
                print('rgb_sworl_test    :' + Fore.RED + Style.BRIGHT + \
                        ' INFO  : timeout waiting to disable rgbmatrix thread for {}.'.format(display_type.name) + Style.RESET_ALL)
                sys.exit(1)
        _rgbmatrix.set_color(Color.BLACK)

        print('rgb_sworl_test    :' + Fore.CYAN + Style.BRIGHT + ' INFO  : {} complete.'.format(display_type.name) + Style.RESET_ALL)

        time.sleep(1.0)

        print('rgb_sworl_test    :' + Fore.CYAN + Style.BRIGHT + ' INFO  : test complete.' + Style.RESET_ALL)

    except KeyboardInterrupt:
        print('rgb_sworl_test    :' + Fore.YELLOW + ' INFO  : Ctrl-C caught: exiting...' + Style.RESET_ALL)
    finally:
        _rgbmatrix.disable()
        _rgbmatrix.close()

if __name__== "__main__":
    main()

#EOF
