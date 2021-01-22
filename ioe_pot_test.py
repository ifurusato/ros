#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# Copyright 2020 by Murray Altheim. All rights reserved. This file is part
# of the pimaster2ardslave project and is released under the MIT Licence;
# please see the LICENSE file included as part of this package.
#
# author:   Murray Altheim
# created:  2020-09-19
# modified: 2020-09-19
#

import math, sys, traceback, time, colorsys
import ioexpander as io
from colorama import init, Fore, Style
init()

from lib.config_loader import ConfigLoader
from lib.logger import Level, Logger
from lib.ioe_pot import Potentiometer

# main .........................................................................
def main(argv):

    try:

        # read YAML configuration
        _loader = ConfigLoader(Level.INFO)
        _config = _loader.configure('config.yaml')

        _pot = Potentiometer(_config, Level.INFO)
        _pot.set_output_limits(0.0, 50.0) 
        _pot.test()

    except KeyboardInterrupt:
        print(Fore.CYAN + Style.BRIGHT + 'caught Ctrl-C; exiting...')

    except Exception:
        print(Fore.RED + Style.BRIGHT + 'error starting ros: {}'.format(traceback.format_exc()) + Style.RESET_ALL)

# call main ....................................................................
if __name__== "__main__":
    main(sys.argv[1:])

# prevent Python script from exiting abruptly
#signal.pause()

#EOF

