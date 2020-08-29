#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# Copyright 2020 by Murray Altheim. All rights reserved. This file is part of
# the Robot OS project and is released under the "Apache Licence, Version 2.0".
# Please see the LICENSE file included as part of this package.
#
# author:   Murray Altheim
# created:  2020-08-15
# modified: 2020-08-15
#
#  A quick rewrite of the LSM303D example file, to be expanded upon later.
#

import sys, time, math
from colorama import init, Fore, Style
init()

from lsm303d import LSM303D

lsm = LSM303D(0x1d) # Change to 0x1e if you have soldered the address jumper

while True:

    xyz = lsm.magnetometer()
    heading = lsm.heading()
    print(("{:+06.2f} : {:+06.2f} : {:+06.2f}").format(*xyz))
#   x = xyz[0]
#   y = xyz[1]
#   z = xyz[2]
#   print(("{:+06.2f} : {:+06.2f} : {:+06.2f}").format(x,y,z))
    time.sleep(1.0/50)

# typical output:
# -00.02 : -00.13 : +00.04
# -00.04 : -00.27 : +00.07
# -00.04 : -00.26 : +00.07
# -00.04 : -00.26 : +00.08
# -00.04 : -00.26 : +00.07
# -00.04 : -00.26 : +00.07
# -00.04 : -00.27 : +00.07
# -00.04 : -00.26 : +00.07
# -00.04 : -00.27 : +00.08
# -00.04 : -00.26 : +00.07
# -00.04 : -00.26 : +00.07
# -00.04 : -00.27 : +00.07
# -00.04 : -00.26 : +00.07

