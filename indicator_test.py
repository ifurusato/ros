#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# Copyright 2020 by Murray Altheim. All rights reserved. This file is part of
# the Robot Operating System project and is released under the "Apache Licence, 
# Version 2.0". Please see the LICENSE file included as part of this package.
#
# author:   Murray Altheim
# created:  2020-06-27
# modified: 2020-06-27
#
#  Tests the Indicator class, which uses a Rgb5x5Matrix display as a sensor indicator.
#

import sys, time, traceback
from colorama import init, Fore, Style
init()

from lib.logger import Level, Logger
from lib.enums import Color
from lib.indicator import Indicator


# main .........................................................................

def main(argv):

    try:
        _log = Logger("indicator_test", Level.INFO)

        _indicator = Indicator(Level.INFO)
        _sleep_sec = 0.2

        _log.info(Fore.CYAN + 'DIR FWD' + Style.RESET_ALL)
        _indicator.set_direction_fwd(True)
        time.sleep(_sleep_sec)
        _indicator.set_direction_fwd(False)

        _log.info(Fore.RED + 'DIR PORT' + Style.RESET_ALL)
        _indicator.set_direction_port(True)
        time.sleep(_sleep_sec)
        _indicator.set_direction_port(False)

        _log.info(Fore.YELLOW + 'DIR AFT' + Style.RESET_ALL)
        _indicator.set_direction_aft(True)
        time.sleep(_sleep_sec)
        _indicator.set_direction_aft(False)

        _log.info(Fore.GREEN + 'DIR STBD' + Style.RESET_ALL)
        _indicator.set_direction_stbd(True)
        time.sleep(_sleep_sec)
        _indicator.set_direction_stbd(False)

        _log.info(Fore.RED + 'PORT SIDE IR' + Style.RESET_ALL)
        _indicator.set_ir_sensor_port_side(True)
        time.sleep(_sleep_sec)
        _indicator.set_ir_sensor_port_side(False)

        _log.info(Fore.RED + 'PORT IR' + Style.RESET_ALL)
        _indicator.set_ir_sensor_port(True)
        time.sleep(_sleep_sec)
        _indicator.set_ir_sensor_port(False)

        _log.info(Fore.CYAN + 'CNTR IR' + Style.RESET_ALL)
        _indicator.set_ir_sensor_center(True)
        time.sleep(_sleep_sec)
        _indicator.set_ir_sensor_center(False)

        _log.info(Fore.GREEN + 'STBD IR' + Style.RESET_ALL)
        _indicator.set_ir_sensor_stbd(True)
        time.sleep(_sleep_sec)
        _indicator.set_ir_sensor_stbd(False)

        _log.info(Fore.GREEN + 'STBD IR' + Style.RESET_ALL)
        _indicator.set_ir_sensor_stbd_side(True)
        time.sleep(_sleep_sec)
        _indicator.set_ir_sensor_stbd_side(False)

        _log.info(Fore.RED + 'PORT BUMPER' + Style.RESET_ALL)
        _indicator.set_bumper_port(True)
        time.sleep(_sleep_sec)
        _indicator.set_bumper_port(False)

        _log.info(Fore.CYAN + 'CNTR BUMPER' + Style.RESET_ALL)
        _indicator.set_bumper_center(True)
        time.sleep(_sleep_sec)
        _indicator.set_bumper_center(False)

        _log.info(Fore.GREEN + 'STBD BUMPER' + Style.RESET_ALL)
        _indicator.set_bumper_stbd(True)
        time.sleep(_sleep_sec)
        _indicator.set_bumper_stbd(False)

        _indicator.clear()

    except KeyboardInterrupt:
        _log.error('caught Ctrl-C; exiting...')
    except Exception:
        _log.error('error starting ros: {}'.format(traceback.format_exc()))


# call main ....................................................................
if __name__== "__main__":
    main(sys.argv[1:])


#EOF
