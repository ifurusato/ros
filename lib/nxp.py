#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# Copyright 2020-2021 by Murray Altheim. All rights reserved. This file is part
# of the Robot Operating System project, released under the MIT License. Please
# see the LICENSE file included as part of this package.
#
# author:   Murray Altheim
# created:  2020-08-23
# modified: 2020-08-31
#
# Wrapper class around the NXP 9 DoF IMU board. See the nxp9dof.py file for
# more details.
#

import time, math
from colorama import init, Fore, Style
init()

from lib.logger import Level, Logger

# ..............................................................................
class NXP():
    '''
    A wrapper class around an NXP 9 DoF IMU.
    '''
    def __init__(self, nxp, level):
        self._log = Logger('nxp-test', level)
        self._imu = nxp.get_imu()
        self._fxos = nxp.get_fxos()
        self._fxas = nxp.get_fxas()
        self._log.info('ready.')

    # ..........................................................................
    @staticmethod
    def to_degrees(radians):
        return math.degrees(radians)

    # ..........................................................................
    def imu(self, count):
        header = 67
        self._log.info('-' * header)
        self._log.info("| {:17} | {:20} | {:20} |".format("Accels [g's]", " Magnet [uT]", "Gyros [dps]"))
        self._log.info('-' * header)
        for _ in range(count):
            a, m, g = self._imu.get()
            self._log.info('| {:>5.2f} {:>5.2f} {:>5.2f} | {:>6.1f} {:>6.1f} {:>6.1f} | {:>6.1f} {:>6.1f} {:>6.1f} |'.format(
                a[0], a[1], a[2],
                m[0], m[1], m[2],
                g[0], g[1], g[2])
            )
            time.sleep(0.50)
        self._log.info('-' * header)
        self._log.info(' uT: micro Tesla')
        self._log.info('  g: gravity')
        self._log.info('dps: degrees per second')
        self._log.info('')

    # ..........................................................................
    def ahrs(self, count):
        self._log.info('')
        header = 47
        self._log.info('-' * header)
        self._log.info("| {:20} | {:20} |".format("Accels [g's]", "Orient(r,p,h) [deg]"))
        self._log.info('-' * header)
        for _ in range(count):
            a, m, g = self._imu.get()
            m = mag_x, mag_y, mag_z
            r, p, h = self._imu.getOrientation(a, m)
            self._log.info(Fore.GREEN + '| {:>6.1f} {:>6.1f} {:>6.1f} | {:>6.1f} {:>6.1f} {:>6.1f} |'.format(a[0], a[1], a[2], r, p, h) + Style.RESET_ALL)
            time.sleep(0.50)
        self._log.info('-' * header)
        self._log.info('  r: roll')
        self._log.info('  p: pitch')
        self._log.info('  h: heading')
        self._log.info('  g: gravity')
        self._log.info('deg: degree')
        self._log.info('')

    # ..........................................................................
    def ahrs2(self, print_info):
        if print_info:
            header = 87  # 47
            self._log.info('-' * header)
            self._log.info(Fore.CYAN + "| {:20} | {:20} | {:20} | {:14} |".format("Accels [g's]", "Magnet [uT]", "Gyros [dps]", "Orient [deg]") + Style.RESET_ALL)
#           self._log.info(Fore.MAGENTA + "| {:20} | {:20} |".format("Accels [g's]", "Orient(r,p,h) [deg]") + Style.RESET_ALL)
#           self._log.info(Fore.CYAN    + "| {:20} | {:20} |".format("Magnet [uT]", "Gyros [dps]") + Style.RESET_ALL)
            self._log.info('-' * header)
#       for _ in range(count):
#       a, m, g = self._imu.get()

        accel_x, accel_y, accel_z = self._fxos.accelerometer

        a = accel_x, accel_y, accel_z

#       a = accel_z, accel_x, accel_y
#       a = accel_y, accel_z, accel_x
#       a = accel_x, accel_y, accel_z
#       a = accel_z, accel_y, accel_x
#       a = accel_x, accel_z, accel_y
#       a = accel_y, accel_x, accel_z

        mag_x, mag_y, mag_z = self._fxos.magnetometer
        m = mag_x, mag_y, mag_z
#       _degrees = Convert.convert_to_degrees(mag_x, mag_y, mag_z)

        gyro_x, gyro_y, gyro_z = self._fxas.gyroscope
        g = gyro_x, gyro_y, gyro_z

        r, p, h = self._imu.getOrientation(a, m)

        _heading = math.degrees(h)
#       _heading_calc = (math.atan2(mag_x, mag_y) * 180.0) / math.pi
        _heading_calc = (math.atan2(mag_z, mag_y) * 180.0) / math.pi
        if _heading_calc < 0:
            _heading_calc += 360

#       _heading_calc = (math.atan2(mag_x, mag_z) * 180.0) / math.pi
#       _heading_calc = (math.atan2(mag_z, mag_x) * 180.0) / math.pi

#       _heading_calc = (math.atan2(mag_z, mag_y) * 180.0) / math.pi
#       _heading_calc = (math.atan2(mag_y, mag_z) * 180.0) / math.pi

        self._log.info(Fore.MAGENTA + '| {:>6.1f} {:>6.1f} {:>6.1f} '.format(a[0], a[1], a[2]) \
                     +Fore.YELLOW + '| {:>6.1f} {:>6.1f} {:>6.1f} '.format(m[0], m[1], m[2]) \
                     +Fore.CYAN + '| {:>6.1f} {:>6.1f} {:>6.1f} '.format(g[0], g[1], g[2]) \
                     +Fore.WHITE + '|' + Style.BRIGHT + ' {:>6.1f}'.format(_heading) + Style.NORMAL + ' {:>6.1f} '.format(_heading_calc) + Style.NORMAL + ' |' + Style.RESET_ALL) # or _heading_calc
#       self._log.info(Fore.CYAN    + '| {:>6.1f} {:>6.1f} {:>6.1f} | {:>6.1f} {:>6.1f} {:>6.1f} |'.format(m[0], m[1], m[2], g[0], g[1], g[2]) + Style.RESET_ALL)
        if print_info and False:
            self._log.info('-' * header)
            self._log.info('  r: roll')
            self._log.info('  p: pitch')
            self._log.info('  h: heading')
            self._log.info('  g: gravity')
            self._log.info('deg: degree')
            self._log.info('')

    # ..........................................................................
    def heading(self):
#   def heading(self, count):
        self._log.info('')
#       for _ in range(count):
        a, m, g = self._imu.get()
        r, p, h = self._imu.getOrientation(a, m)
        mag_x, mag_y, mag_z = self._fxos.magnetometer
        # make easier to read even if completely wrong:
        r = r * 100.0
        p = p * 100.0
        h = h * 100.0
        _heading = math.degrees(h)
#       _heading_calc = (math.atan2(mag_x, mag_y) * 180.0) / math.pi
        _heading_calc = (math.atan2(mag_z, mag_y) * 180.0) / math.pi
        if _heading_calc < 0:
            _heading_calc += 360

        self._log.info(Fore.MAGENTA + 'p: {:>6.4f}\tr: {:>6.4f}\th: {:>6.4f}°; heading: {:>6.4f}°'.format(p, r, h, _heading_calc) + Style.RESET_ALL)
        time.sleep(0.50)

# EOF
