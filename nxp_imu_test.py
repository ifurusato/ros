#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# Copyright 2020 by Murray Altheim. All rights reserved. This file is part of
# the Robot Operating System project and is released under the "Apache Licence,
# Version 2.0". Please see the LICENSE file included as part of this package.
#
# author:   Murray Altheim
# created:  2020-08-23
# modified: 2020-08-31
#
#  Beginnings of a possible replacement for the BNO055 as the source of
#  heading information for the Compass class, instead using the Adafruit
#  Precision NXP 9-DOF Breakout Board - FXOS8700 + FXAS21002, see:
#
#      https://www.adafruit.com/product/3463
#
#  This is very preliminary work and currently non-functional.
#

from colorama import init, Fore, Style
init()

from lib.config_loader import ConfigLoader
from lib.logger import Level, Logger
from lib.queue import MessageQueue
from lib.message_factory import MessageFactory
#rom lib.indicator import Indicator
from lib.nxp9dof import NXP9DoF
from lib.nxp import NXP
from lib.rate import Rate


# ..............................................................................
def main():

    try:

        # read YAML configuration
        _loader = ConfigLoader(Level.INFO)
        filename = 'config.yaml'
        _config = _loader.configure(filename)
        _message_factory = MessageFactory(Level.INFO)
        _queue = MessageQueue(_message_factory, Level.INFO)
        _rate = Rate(5) # 20Hz

        _nxp9dof = NXP9DoF(_config, _queue, Level.INFO)
        _nxp = NXP(_nxp9dof, Level.INFO)

#       _nxp.enable()
#       _nxp9dof.enable()


        _nxp.ahrs2(True)
        while True:
#           _nxp.heading(20)
#           _nxp.ahrs(10)
#           _nxp.imu(10)
            _nxp.ahrs2(False)
            _rate.wait()

    except KeyboardInterrupt:
        print(Fore.RED + 'Ctrl-C caught; exiting...' + Style.RESET_ALL)


if __name__ == "__main__":
    main()

# EOF
