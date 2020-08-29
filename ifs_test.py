#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# Copyright 2020 by Murray Altheim. All rights reserved. This file is part
# of the pimaster2ardslave project and is released under the MIT Licence;
# please see the LICENSE file included as part of this package.
#
# author:   Murray Altheim
# created:  2020-04-30
# modified: 2020-05-24
#
# This tests a hardware configuration of one button, one LED, two digital
# and one analog infrared sensors, first configuring the Arduino and then
# performing a communications loop.
#
# This requires installation of pigpio, e.g.:
#
#   % sudo pip3 install pigpio
#

import time, itertools
from colorama import init, Fore, Style
init()

from lib.logger import Logger, Level
from lib.config_loader import ConfigLoader
from lib.event import Event
from lib.queue import MessageQueue
from lib.ifs import IntegratedFrontSensor
from lib.indicator import Indicator

# ..............................................................................

_ifs = None

def main():

    try:

        # read YAML configuration
        _loader = ConfigLoader(Level.INFO)
        filename = 'config.yaml'
        _config = _loader.configure(filename)

        _queue = MessageQueue(Level.INFO)
        _ifs = IntegratedFrontSensor(_config, _queue, Level.INFO)

        _indicator = Indicator(Level.INFO)
#       _indicator.set_heading(180)
        # add indicator as message consumer
        _queue.add_consumer(_indicator)

        _ifs.enable() 

        while True:
            time.sleep(0.1)

    except KeyboardInterrupt:
        print(Fore.RED + 'Ctrl-C caught; exiting...' + Style.RESET_ALL)
    finally:
        if _ifs is not None:
            _ifs.close()


if __name__== "__main__":
    main()

#EOF
