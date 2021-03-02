#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# Copyright 2020-2021 by Murray Altheim. All rights reserved. This file is part
# of the Robot Operating System project, released under the MIT License. Please
# see the LICENSE file included as part of this package.
#
# author:   Murray Altheim
# created:  2021-03-02
# modified: 2021-03-02
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

import os.path
from os import path
from colorama import init, Fore, Style
init()

_enable_filepath = '/sys/class/pwm/pwmchip0/pwm1/enable'
if path.exists(_enable_filepath):

    f = open(_enable_filepath, "r")
    _contents = f.read().strip()
    print(Fore.YELLOW + 'read "{}" from file: {}'.format(_contents, _enable_filepath) + Style.RESET_ALL)
    f.close()

    _state = '0' if _contents == '1' else '1'

    f = open(_enable_filepath, "w")
    f.write(_state)
    f.close()
    print(Fore.YELLOW + 'wrote {} to enable file: {}'.format(_state, _enable_filepath) + Style.RESET_ALL)
else:
    print(Fore.RED    + 'enable file not found at: {}'.format(_enable_filepath) + Style.RESET_ALL)

#EOF
