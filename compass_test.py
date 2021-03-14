#!/usr/bin/env python3
#
# Copyright 2020-2021 by Murray Altheim. All rights reserved. This file is part
# of the Robot Operating System project, released under the MIT License. Please
# see the LICENSE file included as part of this package.
#
# author:   Murray Altheim
# created:  2019-08-03
# modified: 2019-12-20
#
# Tests an ICM20948 IMU, displaying a cardinal point as a color on an 
# 5x5 RGB LED matrix display.
#

import sys, time, traceback, math
from colorama import init, Fore, Style
init()

try:
    from icm20948 import ICM20948
except ImportError as ie:
    sys.exit("This script requires the icm20948 module.\n"\
           + "Install with: pip3 install --user icm20948")

from lib.enums import Cardinal
from lib.logger import Level, Logger
from lib.config_loader import ConfigLoader
from lib.convert import Convert
from lib.rgbmatrix import RgbMatrix, Color, DisplayType

# ..............................................................................
class IMU():
    '''
    An ICM20948-based Inertial Measurement Unit (IMU).
    '''
    def __init__(self, config, level):
        super().__init__()
        self._log = Logger('imu', level)
        if config is None:
            raise ValueError('no configuration provided.')
        _config = config['ros'].get('imu')
        self._icm20948 = ICM20948(i2c_addr=0x69)
        self._amin = list(self._icm20948.read_magnetometer_data())
        self._amax = list(self._icm20948.read_magnetometer_data())
        self._log.info('amin: {}; amax: {}'.format(type(self._amin), type(self._amax)))
        self._log.info('ready.')

    def read_magnetometer(self):
        return self._icm20948.read_magnetometer_data()

    def read_accelerometer_gyro(self):
        return self._icm20948.read_accelerometer_gyro_data()

#    def heading_from_magnetometer(self, mag):
#        mag = list(mag)
#        for i in range(3):
#            v = mag[i]
#            if v < self._amin[i]:
#                self._amin[i] = v
#            if v > self._amax[i]:
#                self._amax[i] = v
#            mag[i] -= self._amin[i]
#            try:
#                mag[i] /= self._amax[i] - self._amin[i]
#            except ZeroDivisionError:
#                pass
#            mag[i] -= 0.5
#    
#        heading = math.atan2(mag[AXES[0]], mag[AXES[1]])
#        if heading < 0:
#            heading += 2 * math.pi
#        heading = math.degrees(heading)
#        heading = int(round(heading))
#        return heading

# main .........................................................................
def main(argv):

    _rgbmatrix = RgbMatrix(Level.INFO)
    _rgbmatrix.set_display_type(DisplayType.SOLID)
    _rgbmatrix.enable()

    try:

        # read YAML configuration
        _loader = ConfigLoader(Level.INFO)
        filename = 'config.yaml'
        _config = _loader.configure(filename)

        _imu = IMU(_config, Level.INFO)

        while True:
#           x, y, z = _imu.read_magnetometer()
            mag = _imu.read_magnetometer()
#           ax, ay, az, gx, gy, gz = _imu.read_accelerometer_gyro()
            acc = _imu.read_accelerometer_gyro()

            _heading = Convert.heading_from_magnetometer(_imu._amin, _imu._amax, mag)
            _cardinal = Cardinal.get_heading_from_degrees(_heading)
            _color = Cardinal.get_color_for_direction(_cardinal)
            _rgbmatrix.set_color(_color)

            print(Fore.CYAN    + 'Accel: {:05.2f} {:05.2f} {:05.2f} '.format(acc[0], acc[1], acc[2]) \
                + Fore.YELLOW  + '\tGyro: {:05.2f} {:05.2f} {:05.2f} '.format(acc[3], acc[4], acc[5]) \
                + Fore.MAGENTA + '\tMag: {:05.2f} {:05.2f} {:05.2f}  '.format(mag[0], mag[1], mag[2]) \
                + Fore.GREEN   + '\tHeading: {:d}°;\tcardinal: {}'.format(_heading, _cardinal.display) + Style.RESET_ALL)
            time.sleep(0.25)

    except KeyboardInterrupt:
        print(Fore.CYAN + Style.BRIGHT + 'caught Ctrl-C; exiting...')
        
    except Exception:
        print(Fore.RED + Style.BRIGHT + 'error starting imu: {}'.format(traceback.format_exc()) + Style.RESET_ALL)
    finally:
        if _rgbmatrix:
            _rgbmatrix.set_color(Color.BLACK)

# call main ....................................................................
if __name__== "__main__":
    main(sys.argv[1:])

