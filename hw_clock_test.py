#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# Copyright 2020-2021 by Murray Altheim. All rights reserved. This file is part
# of the Robot Operating System project, released under the MIT License. Please
# see the LICENSE file included as part of this package.
#
# author:   Murray Altheim
# created:  2021-03-02
# modified: 2021-03-03
#
# To use one of the Raspberry Pi's hardware clocks as a 20Hz system clock:
#
#   * Edit /boot/config.txt.
#   * Add the line dtoverlay=pwm-2chan
#   * Save the file.
#   * Reboot.
#
# This creates a new directory at:
#
#   /sys/class/pwm/pwmchip0
#
# If you write a "1" to /sys/class/pwm/pwmchip0/export this will create a
# new directory:
#
#   /sys/class/pwm/pwmchip0/pwm1/
#
# which will contain a number of files. For a 20Hz system clock the period
# is 50ms, but must be written to the configuration file in nanoseconds.
# Likewise, the 50% duty cycle is expressed as half of the period and
# written to a separate file. Then a "1" is written to the 'enable' file
# to start the timer:
#
#   echo 50000000 > /sys/class/pwm/pwmchip0/pwm1/period
#   echo 25000000 > /sys/class/pwm/pwmchip0/pwm1/duty_cycle
#   echo 1 > /sys/class/pwm/pwmchip0/pwm1/enable
#
# And that's it. You can connect an LED between BCM pin 19 and ground
# through an appropriate resistor and you'll see it vibrating away at
# 20Hz.
#

import sys, time, traceback
from colorama import init, Fore, Style
init()

from lib.logger import Level, Logger
from lib.hw_clock import HardwareClock


# main .........................................................................
def main(argv):

    try:

        # configure clock on init, will need sudo if not yet configured.
        _hwclock = HardwareClock(Level.INFO)
        _hwclock.add_test_callback()
        _hwclock.enable()
        while _hwclock.enabled:
#           print(Fore.CYAN + 'waiting...')
            time.sleep(1.0)

        print(Fore.CYAN + 'complete.')

    except KeyboardInterrupt:
        print(Fore.CYAN + Style.BRIGHT + 'caught Ctrl-C; exiting...')
    except Exception:
        print(Fore.RED + Style.BRIGHT + 'error configuring hardware clock: {}'.format(traceback.format_exc()) + Style.RESET_ALL)
    finally:
        sys.exit(0)

# call main ....................................................................
if __name__== "__main__":
    main(sys.argv[1:])

#EOF
