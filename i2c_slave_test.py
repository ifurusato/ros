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
# This tests the hardware configuration determined by the config.yaml file.
# This is generally the configuration of the integrated Front Bumper, which
# includes five analog infrared sensors (A0-A4) and three bumpers (pins 9-11).
#

from lib.logger import Level
from lib.i2c_master import I2cMaster
from lib.config_loader import ConfigLoader

# ..............................................................................
def main():

    try:

        # read YAML configuration
        _loader = ConfigLoader(Level.INFO)
        filename = 'config.yaml'
        _config = _loader.configure(filename)

        _loop_count = 10000
        _master = I2cMaster(_config, Level.INFO)

        if _master is not None:

            # set it to some very large number if you want it to go on for a long time...
#           _master.test_echo() # see documentation for hardware configuration
            _master.test_configuration(_loop_count) # see documentation for hardware configuration

        else:
            raise Exception('unable to establish contact with Arduino on address 0x{:02X}'.format(_device_id))

    except KeyboardInterrupt:
        self._log.warning('Ctrl-C caught; exiting...')
    finally:
        if _master:
            _master.close()


if __name__== "__main__":
    main()

#EOF
