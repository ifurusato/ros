#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# Copyright 2020 by Murray Altheim. All rights reserved. This file is part of
# the Robot OS project and is released under the "Apache Licence, Version 2.0".
# Please see the LICENSE file included as part of this package.
#
# author:   Murray Altheim
# created:  2020-08-15
# modified: 2020-08-28
#
# Tests the ICM20948 and Compass class (which uses a BNO055) for an IMU fusion
# used solely for reading an absolute heading (i.e., as a compass).
#

import pytest
import time, sys, traceback
from colorama import init, Fore, Style
init()

from lib.config_loader import ConfigLoader
from lib.logger import Level, Logger
from lib.convert import Convert
from icm20948 import ICM20948
from lib.bno055 import BNO055

# ..............................................................................
class IMU():
    '''
    Composite IMU.
    '''
    def __init__(self, config, level):
        self._log = Logger("imu", level)
        if config is None:
            raise ValueError("no configuration provided.")
        # ICM20948 configuration .....................................
        _icm20948_config = config['ros'].get('icm20948')
        self._icm20948_heading_trim = _icm20948_config.get('heading_trim')
        self._log.info('trim: heading: {:<5.2f}° (ICM20948)'.format(self._icm20948_heading_trim))
        self._icm20948 = ICM20948(i2c_addr=0x69)
        self._amin = list(self._icm20948.read_magnetometer_data())
        self._amax = list(self._icm20948.read_magnetometer_data())
        # BNO055 configuration .......................................
        self._bno055 = BNO055(config, Level.INFO)

        self._log.info('ready.')

    # ..........................................................................
    def read_icm20948_magnetometer(self):
        return self._icm20948.read_magnetometer_data()

    # ..........................................................................
    def read_icm20948_accelerometer_gyro_data(self):
        # ax, ay, az, gx, gy, gz = _imu.read_accelerometer_gyro()
        return self._icm20948.read_accelerometer_gyro_data()

    # ..........................................................................
    def read_icm20948_heading(self):
        _mag = self._icm20948.read_magnetometer_data()
        _orig_heading = Convert.heading_from_magnetometer(self._amin, self._amax, _mag)
        _heading = Convert.offset_in_degrees(_orig_heading, self._icm20948_heading_trim)
        self._log.info(Fore.GREEN + 'heading:\t{:>5.2f}°\t'.format(_heading) + Style.DIM + '(icm20948; orig: {:>5.2f}°)'.format(_orig_heading))
        return _heading

    # ..........................................................................
    def read_bno055_heading(self):
        _bno_reading = self._bno055.read()
        return _bno_reading

    # ..........................................................................
    def read_heading(self):
        '''
        Read a composite heading.
        '''
        _bno_reading = self.read_bno055_heading()
        _bno_heading = _bno_reading[1]
        _icm20948_heading = self.read_icm20948_heading()
        _diff = _bno_heading = _icm20948_heading
        if _diff < 90.0:
            self._log.info(Fore.CYAN + 'diff: {:5.2f}°\t'.format(_diff) + Fore.BLACK + '(bno: {:5.2f}°; icm: {:5.2f}°)'.format(_bno_heading, _icm20948_heading))
        else:
            self._log.info(Fore.YELLOW + 'diff: {:5.2f}°\t'.format(_diff) + Fore.BLACK + '(bno: {:5.2f}°; icm: {:5.2f}°)'.format(_bno_heading, _icm20948_heading))


# ..............................................................................
@pytest.mark.unit
def test_imu():
    _log = Logger("imu-test", Level.INFO)
    _loader = ConfigLoader(Level.INFO)
    filename = 'config.yaml'
    _config = _loader.configure(filename)
    _imu = IMU(_config, Level.INFO)
    while True:
        _reading = _imu.read_heading()
        time.sleep(2.0)

# ..............................................................................
def main():
    try:
        test_imu()
    except KeyboardInterrupt:
        print(Fore.RED + 'Ctrl-C caught: complete.')
    except Exception as e:
        print(Fore.RED + 'error closing: {}\n{}'.format(e, traceback.format_exc()))

if __name__== "__main__":
    main()

#EOF
