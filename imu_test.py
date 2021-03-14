#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# Copyright 2020-2021 by Murray Altheim. All rights reserved. This file is part
# of the Robot Operating System project, released under the MIT License. Please
# see the LICENSE file included as part of this package.
#
# author:   Murray Altheim
# created:  2020-08-15
# modified: 2020-08-28
#
# Tests the ICM20948 and Compass class (which uses a BNO055) for an IMU fusion
# used solely for reading an absolute heading (i.e., as a compass). This also
# provides for an optional RGBMatrix 5x5 display.
#
# We know that if an object is not moving it will experience acceleration
# only due to gravity (neglect the other minimal forces). The direction of
# gravitational force is always same with respect to the earth’s frame but
# based on the orientation of IMU, it will experience different amount of
# acceleration along the three axes. These acceleration values can give us
# roll and pitch values.
#
#   pitch = 180 * atan2(accelX, sqrt(accelY*accelY + accelZ*accelZ))/PI;
#   roll  = 180 * atan2(accelY, sqrt(accelX*accelX + accelZ*accelZ))/PI;
#
# As in accelerometer one can use the X, Y and Z magnetometer readings to
# calculate yaw.
#
#   mag_x = magReadX*cos(pitch) + magReadY*sin(roll)*sin(pitch) + magReadZ*cos(roll)*sin(pitch)
#   mag_y = magReadY * cos(roll) - magReadZ * sin(roll)
#   yaw   = 180 * atan2(-mag_y,mag_x)/M_PI;
#

import pytest
import time, sys, traceback
from colorama import init, Fore, Style
init()

from lib.i2c_scanner import I2CScanner
from lib.config_loader import ConfigLoader
from lib.logger import Level, Logger
from lib.convert import Convert
from lib.enums import Cardinal
from lib.rgbmatrix import RgbMatrix, Color, DisplayType

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
        self._log.info(Fore.GREEN + 'heading:\t{:>9.2f}°\t'.format(_heading) + Style.DIM \
                + 'orig: {:>9.2f}°\ttrim: {:>9.2f}°; icm20948'.format(_orig_heading, self._icm20948_heading_trim))
        return _heading

    # ..........................................................................
    def read_bno055_heading(self):
        _bno_reading = self._bno055.read()
        return _bno_reading

    # ..........................................................................
    def read_heading(self):
        '''
        Read a composite heading, returning the BNO055 and ICM20948 values as a tuple.
        '''
        _bno_reading      = self.read_bno055_heading()
        _bno_heading      = _bno_reading[1]
        _icm20948_heading = self.read_icm20948_heading()
        if _bno_heading and _icm20948_heading:
            _diff = _bno_heading - _icm20948_heading
            if _diff < 90.0:
                self._log.info(Fore.CYAN + 'diff: {:5.2f}°\t'.format(_diff) + Fore.BLACK + '(bno: {:5.2f}°; icm: {:5.2f}°)'.format(_bno_heading, _icm20948_heading))
            else:
                self._log.info(Fore.YELLOW + 'diff: {:5.2f}°\t'.format(_diff) + Fore.BLACK + '(bno: {:5.2f}°; icm: {:5.2f}°)'.format(_bno_heading, _icm20948_heading))
            return [ _bno_heading, _icm20948_heading ]
        else:
            self._log.info('unavailable.')
            return [ -1.0, -1.0 ]

# ..............................................................................
@pytest.mark.unit
def test_imu():
    _log = Logger("imu-test", Level.INFO)

    _i2c_scanner = I2CScanner(Level.WARN)
    _addresses = _i2c_scanner.get_addresses()

    _rgbmatrix = RgbMatrix(Level.INFO) if (0x74 in _addresses) else None
    if _rgbmatrix:
        _rgbmatrix.set_display_type(DisplayType.SOLID)
        _rgbmatrix.enable()

    try:

        _loader = ConfigLoader(Level.INFO)
        filename = 'config.yaml'
        _config = _loader.configure(filename)
        _cardinal = Cardinal.get_heading_from_degrees(0)
        _imu = IMU(_config, Level.INFO)

        while True:
            _heading = _imu.read_heading()[0]
            if _rgbmatrix:
                _cardinal = Cardinal.get_heading_from_degrees(_heading)
                _color = Cardinal.get_color_for_direction(_cardinal)
                _rgbmatrix.set_color(_color)
            _log.info(Fore.YELLOW + 'heading: {:05.2f}°;\tcardinal: {}'.format(_heading, _cardinal.display) + Style.RESET_ALL)
            time.sleep(2.0)

    except KeyboardInterrupt:
        _log.info('Ctrl-C caught: exiting...')
    except Exception as e:
        _log.error('error closing: {}\n{}'.format(e, traceback.format_exc()))
    finally:
        if _rgbmatrix:
            _rgbmatrix.set_color(Color.BLACK)
            _rgbmatrix.disable()
        _log.info('complete.')

# ..............................................................................
def main():
    test_imu()

if __name__== "__main__":
    main()

#EOF
