#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# Copyright 2020 by Murray Altheim. All rights reserved. This file is part of
# the Robot Operating System project and is released under the "Apache Licence, 
# Version 2.0". Please see the LICENSE file included as part of this package.
#
# author:   Murray Altheim
# created:  2020-09-02
# modified: 2020-09-02
#

import sys, time, busio, board, traceback
from colorama import init, Fore, Style
init()

try:
    import adafruit_ina260
except ImportError:
    exit("This script requires the numpy module\nInstall with: sudo pip3 install adafruit-circuitpython-ina260")


# main .........................................................................
def main(argv):

    try:

        print(Fore.GREEN + 'start.' + Style.RESET_ALL)

        i2c = busio.I2C(board.SCL, board.SDA)
#       i2c = board.I2C()
#       ina260 = adafruit_ina260.INA260(i2c)
        ina260 = adafruit_ina260.INA260(i2c, address=0x44)

        while True:
            print(Fore.MAGENTA    + 'current: {:>5.2f}mA'.format(ina260.current) \
                    + Fore.CYAN   + '\tvoltage: {:>5.2f}V'.format(ina260.voltage) \
                    + Fore.YELLOW + '\tpower: {:>5.2f}mW'.format(ina260.power) \
                    + Style.RESET_ALL)
            time.sleep(1.0)

        print(Fore.GREEN + 'end.' + Style.RESET_ALL)

    except KeyboardInterrupt:
        print(Fore.CYAN + Style.BRIGHT + 'caught Ctrl-C; exiting...')
    except Exception:
        print(Fore.RED + Style.BRIGHT + 'error starting ina260: {}'.format(traceback.format_exc()) + Style.RESET_ALL)

# call main ....................................................................
if __name__== "__main__":
    main(sys.argv[1:])

# prevent Python script from exiting abruptly
#signal.pause()

#EOF
