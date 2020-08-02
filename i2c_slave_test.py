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
from lib.i2c_ifs import I2cMaster
from lib.config_loader import ConfigLoader

# ..............................................................................
def main():

    try:

        # read YAML configuration
        _loader = ConfigLoader(Level.INFO)
        filename = 'config.yaml'
        _config = _loader.configure(filename)

        _loop_delay_sec = 0.7
        _loop_count = 10000
        _master = I2cMaster(_config, Level.INFO)

        _master.enable()
        if not _master.in_loop():
            _master.start_front_sensor_loop(_loop_delay_sec, self._callback_front)
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
