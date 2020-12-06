#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# Copyright 2020 by Murray Altheim. All rights reserved. This file is part of
# the Robot Operating System project and is released under the "Apache Licence,
# Version 2.0". Please see the LICENSE file included as part of this package.
#
# author:   Murray Altheim
# created:  2020-03-27
# modified: 2020-03-27
#
#  Beginnings of a possible replacement for the BNO055 as the source of
#  heading information for the Compass class, instead using the Adafruit
#  Precision NXP 9-DOF Breakout Board - FXOS8700 + FXAS21002, see:
#
#      https://www.adafruit.com/product/3463
#
#  This is very preliminary work and currently non-functional.
#
# see: https://www.allaboutcircuits.com/technical-articles/how-to-interpret-IMU-sensor-data-dead-reckoning-rotation-matrix-creation/
#      https://roboticsclubiitk.github.io/2017/12/21/Beginners-Guide-to-IMU.html
#      https://embeddedinventor.com/what-is-an-imu-sensor-a-complete-guide-for-beginners/
#      https://pypi.org/project/nxp-imu/
#      https://ozzmaker.com/berryimu/
#

import sys, time, math, board, busio, threading
from colorama import init, Fore, Style
init()

try:
    from nxp_imu import IMU
except ImportError as ie:
    print(Fore.RED + 'unable to import nxp-imu: {}'.format(ie))
    sys.exit("This script requires the nxp-imu module.\n"\
           + "Install with: sudo pip3 install nxp-imu")

try:
    import adafruit_fxos8700
    import adafruit_fxas21002c
except ImportError as ie:
    print(Fore.RED + 'unable to import adafruit_extended_bus: {}'.format(ie))
    sys.exit("This script requires the adafruit-circuitpython-fxos8700 and adafruit-circuitpython-fxas21002c modules.\n"\
           + "Install with: sudo pip3 install adafruit-circuitpython-fxos8700 adafruit-circuitpython-fxas21002c")

#from squaternion import quat2euler
try:
    from pyquaternion import Quaternion
except ImportError:
    sys.exit("This script requires the pyquaternion module.\nInstall with: sudo pip3 install pyquaternion")

from lib.logger import Level, Logger
from lib.message import Message
from lib.convert import Convert
from lib.rate import Rate

# ..............................................................................
class NXP9DoF:
    '''
        Reads from an Adafruit NXP 9-DoF FXOS8700 + FXAS21002 sensor. 

        Note that this has been calibrated based on the orientation of the
        NXP9DoF board as installed on the KR01 robot, with the Adafruit
        logo on the chip (mounted horizontally) as follows:

                                    Fore
                              _---------------
                              |           *  |
                              |              |
                              |              |
                       Port   |              | Starboard
                              |              |
                              ----------------
                                    Aft

        If you mount the chip in a different orientation you will likely
        need to multiply one or more of the axis by -1.0.

        Depending on where you are on the Earth, true North changes because
        the Earth is not a perfect sphere. You can get the declination angle
        for your location from:

            http://www.magnetic-declination.com/

        E.g., for Pukerua Bay, New Zealand:

            Latitude:  41° 1' 57.7" S
            Longitude: 174° 53' 11.8" E
            PUKERUA BAY
            Magnetic Declination: +22° 37'
            Declination is POSITIVE (EAST)
            Inclination: 66° 14'
            Magnetic field strength: 55716.5 nT

        E.g., for Wellington, New Zealand:

            Latitude:  41° 17' 11.9" S
            Longitude: 174° 46' 32.1" E
            KELBURN
            Magnetic Declination: +22° 47'
            Declination is POSITIVE (EAST)
            Inclination: 66° 28'
            Magnetic field strength: 55863.3 nT
    '''

    # permitted error between Euler and Quaternion (in degrees) to allow setting value
    ERROR_RANGE = 5.0  # was 3.0

    # ..........................................................................
    def __init__(self, config, queue, level):
        self._log = Logger("nxp9dof", level)
        if config is None:
            raise ValueError("no configuration provided.")
        self._config = config
        self._queue = queue

        _config = self._config['ros'].get('nxp9dof')
        self._quaternion_accept = _config.get('quaternion_accept') # permit Quaternion once calibrated
        self._loop_delay_sec = _config.get('loop_delay_sec')

        # verbose will print some start-up info on the IMU sensors
        self._imu = IMU(gs=4, dps=2000, verbose=True)
        # setting a bias correction for the accel only; the mags/gyros are not getting a bias correction
        self._imu.setBias((0.0,0.0,0.0), None, None)
#       self._imu.setBias((0.1,-0.02,.25), None, None)

        _i2c = busio.I2C(board.SCL, board.SDA)
        self._fxos = adafruit_fxos8700.FXOS8700(_i2c)
        self._log.info('accelerometer and magnetometer ready.')
        self._fxas = adafruit_fxas21002c.FXAS21002C(_i2c)
        self._log.info('gyroscope ready.')

        self._thread  = None
        self._enabled = False
        self._closed  = False
        self._heading = None
        self._pitch   = None
        self._roll    = None
        self._is_calibrated = False
        self._log.info('ready.')

    # ..........................................................................
    def get_imu(self):
        return self._imu

    # ..........................................................................
    def get_fxos(self):
        return self._fxos

    # ..........................................................................
    def get_fxas(self):
        return self._fxas

    # ..........................................................................
    def enable(self):
        if not self._closed:
            self._enabled = True
            # if we haven't started the thread yet, do so now...
            if self._thread is None:
                self._thread = threading.Thread(target=NXP9DoF._read, args=[self])
                self._thread.start()
            self._log.info('enabled.')
        else:
            self._log.warning('cannot enable: already closed.')

    # ..........................................................................
    def get_heading(self):
        return self._heading

    # ..........................................................................
    def get_pitch(self):
        return self._pitch

    # ..........................................................................
    def get_roll(self):
        return self._roll

    # ..........................................................................
    def is_calibrated(self):
        return self._is_calibrated

    # ..........................................................................
    @staticmethod
    def _in_range(p, q):
        return p >= ( q - NXP9DoF.ERROR_RANGE ) and p <= ( q + NXP9DoF.ERROR_RANGE )

    # ..........................................................................
    def imu_enable(self):
        '''
            Enables the handbuilt IMU on a 20Hz loop.
        '''
        if not self._closed:
            self._enabled = True
            # if we haven't started the thread yet, do so now...
            if self._thread is None:
                self._thread = threading.Thread(target=NXP9DoF._handbuilt_imu, args=[self])
                self._thread.start()
            self._log.info('enabled.')
        else:
            self._log.warning('cannot enable: already closed.')

    # ..........................................................................
    def _handbuilt_imu(self):
        '''
            The function that reads sensor values in a loop. This checks to see
            if the 'sys' calibration is at least 3 (True), and if the Euler and
            Quaternion values are within an error range of each other, this sets
            the class variable for heading, pitch and roll. If they aren't within
            range for more than n polls, the values revert to None.
        '''
        self._log.info('starting sensor read...')
        _heading = None
        _pitch   = None
        _roll    = None
        _quat_w  = None
        _quat_x  = None
        _quat_y  = None
        _quat_z  = None
        count = 0
#               2. Absolute Orientation (Quaterion, 100Hz) Four point quaternion output for more accurate data manipulation ................

        # grab data at 20Hz
        _rate = Rate(1)

        header = 90
        print('-'*header)
#       print("| {:17} | {:20} |".format("Accels [g's]", " IMU Accels"))
        print("| {:17} |".format("Mag [xyz]"))

        while not self._closed:
            if self._enabled:

                accel_x, accel_y, accel_z = self._fxos.accelerometer # m/s^2
                gyro_x, gyro_y, gyro_z    = self._fxas.gyroscope # radians/s
                a, m, g = self._imu.get()
                mag_x, mag_y, mag_z       = self._fxos.magnetometer # uTesla

                mag_x_g = m[0] * 100.0
                mag_y_g = m[1] * 100.0
                mag_z_g = m[2] * 100.0

#               rate_gyro_x_dps = Convert.rps_to_dps(gyro_x)
#               rate_gyro_y_dps = Convert.rps_to_dps(gyro_y)
#               rate_gyro_z_dps = Convert.rps_to_dps(gyro_z)

#               mag_x_g = mag_x * 100.0
#               mag_y_g = mag_y * 100.0
#               mag_z_g = mag_z * 100.0

                heading = 180.0 * math.atan2(mag_y_g,mag_x_g)/math.pi

                print(Fore.CYAN + '| x{:>6.3f} y{:>6.3f} z{:>6.3f} |'.format( mag_x_g, mag_y_g, mag_z_g) \
                        + Style.BRIGHT + '\t{:>5.2f}'.format(heading) + Style.RESET_ALL)


#               a, m, g = self._imu.get()

#               print(Fore.CYAN + '| {:>6.3f} {:>6.3f} {:>6.3f} | {:>6.3f} {:>6.3f} {:>6.3f} |'.format( accel_x, accel_y, accel_z, a[0], a[1], a[2]) + Style.RESET_ALL)

                _rate.wait()

#                   + Style.BRIGHT + ' {:>6.1f} {:>6.1f} {:>6.1f}° |'.format(r, p, deg) + Style.RESET_ALL)
#                   time.sleep(0.50)

#               mag_x, mag_y, mag_z       = self._fxos.magnetometer # uTesla
#               gyro_x, gyro_y, gyro_z    = self._fxas.gyroscope # radians/s


#               header = 90
#               print('-'*header)
#               print("| {:17} | {:20} | {:20} | {:20} |".format("Accels [g's]", " Magnet [uT]", "Gyros [dps]", "Roll, Pitch, Heading"))
#               print('-'*header)
#               for _ in range(10):
#                   a, m, g = self._imu.get()
#                   r, p, h = self._imu.getOrientation(a, m)
#                   deg = Convert.to_degrees(h)
#                   print(Fore.CYAN + '| {:>5.2f} {:>5.2f} {:>5.2f} | {:>6.1f} {:>6.1f} {:>6.1f} | {:>6.1f} {:>6.1f} {:>6.1f} |'.format(
#                       a[0], a[1], a[2],
#                       m[0], m[1], m[2],
#                       g[0], g[1], g[2])
#                   + Style.BRIGHT + ' {:>6.1f} {:>6.1f} {:>6.1f}° |'.format(r, p, deg) + Style.RESET_ALL)
#                   time.sleep(0.50)
#               print('-'*header)
#               print(' uT: micro Tesla')
#               print('  g: gravity')
#               print('dps: degrees per second')
#               print('')

#
#               print(Fore.MAGENTA + 'acc: ({0:0.3f}, {1:0.3f}, {2:0.3f})'.format(accel_x, accel_y, accel_z)\
#                   + Fore.YELLOW  + ' \tmag: ({0:0.3f}, {1:0.3f}, {2:0.3f})'.format(mag_x, mag_y, mag_z)\
#                   + Fore.CYAN    + ' \tgyr: ({0:0.3f}, {1:0.3f}, {2:0.3f})'.format(gyro_x, gyro_y, gyro_z) + Style.RESET_ALL)

            else:
                self._log.info('disabled loop.')
                time.sleep(10)
            count += 1

        self._log.debug('read loop ended.')


    # ..........................................................................
    def _read(self):
        '''
            The function that reads sensor values in a loop. This checks to see
            if the 'sys' calibration is at least 3 (True), and if the Euler and
            Quaternion values are within an error range of each other, this sets
            the class variable for heading, pitch and roll. If they aren't within
            range for more than n polls, the values revert to None.
        '''
        self._log.info('starting sensor read...')
        _heading = None
        _pitch   = None
        _roll    = None
        _quat_w  = None
        _quat_x  = None
        _quat_y  = None
        _quat_z  = None
        count = 0
#               2. Absolute Orientation (Quaterion, 100Hz) Four point quaternion output for more accurate data manipulation ................

        # grab data at 10Hz
        rate = Rate(10)

        while not self._closed:
            if self._enabled:

                header = 91
                print(Fore.CYAN + ('-'*header) + Style.RESET_ALL)
                print(Fore.CYAN + "| {:17} | {:20} | {:20} | {:21} |".format("Accels [g's]", " Magnet [uT]", "Gyros [dps]", "Roll, Pitch, Heading") + Style.RESET_ALL)
                print(Fore.CYAN + ('-'*header) + Style.RESET_ALL)
                for _ in range(10):
                    a, m, g = self._imu.get()
                    r, p, h = self._imu.getOrientation(a, m)
                    deg = Convert.to_degrees(h)
#                   self._log.info(Fore.GREEN + '| {:>6.1f} {:>6.1f} {:>6.1f} | {:>6.1f} {:>6.1f} {:>6.1f} |'.format(a[0], a[1], a[2], r, p, h) + Style.RESET_ALL)
                    print(Fore.CYAN        + '| {:>5.2f} {:>5.2f} {:>5.2f} '.format(a[0], a[1], a[2]) 
                            + Fore.YELLOW  + '| {:>6.1f} {:>6.1f} {:>6.1f} '.format(m[0], m[1], m[2]) 
                            + Fore.MAGENTA + '| {:>6.1f} {:>6.1f} {:>6.1f} '.format(g[0], g[1], g[2])
                            + Fore.GREEN   + '| {:>6.1f} {:>6.1f} {:>6.1f}° |'.format(r, p, deg) + Style.RESET_ALL)
                    time.sleep(0.50)
                print('-'*header)
                print(' uT: micro Tesla')
                print('  g: gravity')
                print('dps: degrees per second')
                print('')

#               accel_x, accel_y, accel_z = self._fxos.accelerometer # m/s^2
#               mag_x, mag_y, mag_z       = self._fxos.magnetometer # uTesla
#               gyro_x, gyro_y, gyro_z    = self._fxas.gyroscope # radians/s
#
#               print(Fore.MAGENTA + 'acc: ({0:0.3f}, {1:0.3f}, {2:0.3f})'.format(accel_x, accel_y, accel_z)\
#                   + Fore.YELLOW  + ' \tmag: ({0:0.3f}, {1:0.3f}, {2:0.3f})'.format(mag_x, mag_y, mag_z)\
#                   + Fore.CYAN    + ' \tgyr: ({0:0.3f}, {1:0.3f}, {2:0.3f})'.format(gyro_x, gyro_y, gyro_z) + Style.RESET_ALL)

                rate.wait()
            else:
                self._log.info('disabled loop.')
                time.sleep(10)
            count += 1

        self._log.debug('read loop ended.')

    # ..........................................................................
    def disable(self):
        self._enabled = False
        self._log.info('disabled.')

    # ..........................................................................
    def close(self):
        self._closed = True
        self._log.info('closed.')

#EOF
