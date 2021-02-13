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

import pytest
import sys, traceback
from colorama import init, Fore, Style
init()

from lib.config_loader import ConfigLoader
from lib.logger import Level, Logger
from lib.ioe_pot import Potentiometer
from lib.rate import Rate

# ..............................................................................
@pytest.mark.unit
def test_ioe_potentiometer():

    _log = Logger("test-ioe-pot", Level.INFO)
    _log.info(Fore.RED + 'to kill type Ctrl-C')

    # read YAML configuration
    _loader = ConfigLoader(Level.INFO)
    _config = _loader.configure('config.yaml')

    _pot = Potentiometer(_config, Level.INFO)
    _pot.set_output_limits(0.00, 0.150) 

    _log.info('starting test...')
    _hz = 10
    _rate = Rate(_hz, Level.ERROR)
    while True:
#       _value = self.get_value()
#       self.set_rgb(_value)
#       _scaled_value = self.scale_value() # as float
        _scaled_value = _pot.get_scaled_value(True)
#       _scaled_value = math.floor(self.scale_value()) # as integer
        _log.info(Fore.YELLOW + 'scaled value: {:9.6f}'.format(_scaled_value))
        _rate.wait()


# main .........................................................................
def main(argv):

    try:
        test_ioe_potentiometer()
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

