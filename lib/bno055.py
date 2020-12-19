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

import sys
from enum import Enum
import adafruit_bno055
from colorama import init, Fore, Style
init()

try:
    from adafruit_extended_bus import ExtendedI2C as I2C
except ImportError as ie:
    print(Fore.RED + 'unable to import adafruit_extended_bus: {}'.format(ie))
    sys.exit("This script requires the adafruit-circuitpython-register and adafruit-circuitpython-busdevice modules.\n"\
           + "Install with: sudo pip3 install adafruit-circuitpython-register adafruit-circuitpython-busdevice")

try:
    from pyquaternion import Quaternion
except ImportError:
    sys.exit("This script requires the pyquaternion module.\nInstall with: sudo pip3 install pyquaternion")

from lib.logger import Level, Logger
from lib.message import Message
from lib.convert import Convert

# ..............................................................................
class BNO055:
    '''
        Reads from a BNO055 9DoF sensor. Earlier versions of this class dealt
        with 3D values; this has been simplified and is now used only for 
        absolute compass orientation and hence only returns heading values
        (not pitch, roll, etc.)

        Note that the calibration is based on the orientation of the BNO055
        board as installed on the KR01 robot (ie., mounted horizontally), 
        with the dot on the chip as follows:

                                    Fore
                               --------------
                               |         •  |
                               |            |
                               |            |
                        Port   |            | Starboard
                               |            |
                               --------------
                                    Aft

        If you mount the chip in a different orientation you will likely
        need to multiply one or more of the axis by -1.0.

        If you only rotate the chip along the horizontal plane you can 
        alter the configuration for the heading trim value.
    '''
        
    def __init__(self, config, level):
        self._log = Logger("bno055", level)
        if config is None:
            raise ValueError("no configuration provided.")

        self._config = config
        # config
        _config = self._config['ros'].get('bno055')
        self._bno_mode           = BNO055Mode.from_name(_config.get('mode'))
#       self._pitch_trim         = _config.get('pitch_trim')
#       self._roll_trim          = _config.get('roll_trim')
        self._euler_heading_trim = _config.get('euler_heading_trim')
        self._quat_heading_trim  = _config.get('quat_heading_trim')
        self._log.info('trim: heading: {:>5.2f}°(Euler) / {:>5.2f}°(Quat); pitch: {:>5.2f}°; roll: {:>5.2f}°'.format(\
                self._euler_heading_trim, self._quat_heading_trim, self._pitch_trim, self._roll_trim))
        self._error_range       = 5.0 # permitted error between Euler and Quaternion (in degrees) to allow setting value, was 3.0
        # use `ls /dev/i2c*` to find out what i2c devices are connected
        _i2c_device             = _config.get('i2c_device')
        self._bno055 = adafruit_bno055.BNO055_I2C(I2C(_i2c_device)) # Device is /dev/i2c-1
        # some of the modes provide accurate compass calibration but are very slow to calibrate
#       self.set_mode(BNO055Mode.CONFIG_MODE)
#       self._bno055.mode = BNO055Mode.COMPASS_MODE.mode 
#       self._bno055.mode = BNO055Mode.NDOF_FMC_OFF_MODE.mode
        self.set_mode(self._bno_mode)
        self._heading = 0.0
#       self._pitch   = None
#       self._roll    = None
        self._is_calibrated = Calibration.NEVER
        self._log.info('ready.')

    # ..........................................................................
    def set_mode(self, mode):
        if not isinstance(mode, BNO055Mode):
            raise Exception('argument was not a BNO055Mode object.')
        self._bno055.mode = mode.mode
        self._log.info(Fore.YELLOW + 'BNO055 mode set to: {}'.format(mode.name))

    # ..........................................................................
    def is_calibrated(self):
        return self._is_calibrated

    # ..........................................................................
    def get_calibration_status(self):
        # status: sys, gyro, accel, mag
        _status = self._bno055.calibration_status
        _sys_calibrated = ( _status[0] >= 3 )
        _gyr_calibrated = ( _status[1] >= 3 )
        _acc_calibrated = ( _status[2] >= 2 )
        _mag_calibrated = ( _status[3] >= 2 )

        # "Therefore we recommend that as long as Magnetometer is 3/3, and Gyroscope is 3/3, the data can be trusted."
        # source: https://community.bosch-sensortec.com/t5/MEMS-sensors-forum/BNO055-Calibration-Staus-not-stable/td-p/8375
#       _ok_calibrated = _gyr_calibrated and _mag_calibrated
        _ok_calibrated = _gyr_calibrated 
        _show_always = True

        # show calibration of each sensor
        if _show_always or not _ok_calibrated:
            self._log.info( Fore.MAGENTA + ( Style.BRIGHT if _sys_calibrated else Style.DIM ) + ' s{}'.format(_status[0]) + Style.NORMAL \
                          + Fore.YELLOW  + ( Style.BRIGHT if _gyr_calibrated else Style.DIM ) + ' g{}'.format(_status[1]) + Style.NORMAL \
                          + Fore.GREEN   + ( Style.BRIGHT if _acc_calibrated else Style.DIM ) + ' a{}'.format(_status[2]) + Style.NORMAL \
                          + Fore.CYAN    + ( Style.BRIGHT if _mag_calibrated else Style.DIM ) + ' m{}'.format(_status[3]) + Style.NORMAL )
            self._is_calibrated = Calibration.LOST
        else:
            self._is_calibrated = Calibration.CALIBRATED
        return self._is_calibrated

    # ..........................................................................
    def get_heading(self):
        '''
        Returns a tuple containing a Calibration (enum) indicating if the sensor
        is calibrated followed by the heading value. Note that this only returns
        the last results following a read() and not new values.
        '''
        return ( self._is_calibrated, self._heading )

#   # ..........................................................................
#   def get_pitch(self):
#       return self._pitch

#   # ..........................................................................
#   def get_roll(self):
#       return self._roll

    # ..........................................................................
    def read(self):
        '''
        The function that reads multiple sensor values. This checks to see if
        the 'sys' calibration is at least 3 (True), and if the Euler and
        Quaternion values are within an error range of each other, this sets
        the class variable self._heading, pitch and roll. If they aren't within
        range for more than n polls, the values revert to None.

        Returns a tuple containing the calibration status followed by the
        Euler and Quaternion headings.
        '''
        self._log.debug('starting sensor read...')
        _e_heading, _e_pitch, _e_roll, _e_yaw, _orig_quat_heading, _q_pitch, _q_roll, _q_yaw = [None] * 8
        _quat_w = 0
        _quat_x = 0
        _quat_y = 0
        _quat_z = 0

        self.get_calibration_status()

        _euler = self._bno055.euler
        if _euler != None and _euler[0] != None:
#           self._log.info(Fore.BLUE + Style.NORMAL + 'euler: {:>5.4f}°'.format(_euler))
#           self._log.info(Fore.BLUE + Style.NORMAL + 'euler: {:>5.4f}°'.format(_euler[0]))
            _orig_euler_heading = _euler[0]
            _euler_converted_heading = Convert.offset_in_degrees(_orig_euler_heading, self._euler_heading_trim)
            self._log.info(Fore.BLUE + Style.NORMAL + 'heading:\t{:>6.2f}°\t(euler; orig: {:>6.2f}°)'.format(_euler_converted_heading, _orig_euler_heading))
        else:
            self._log.info(Fore.BLUE + Style.DIM + 'heading:\tNA\t(euler)')

        # BNO055 Absolute Orientation (Quaterion, 100Hz) Four point quaternion output for more accurate data manipulation ..............
        _quat = self._bno055.quaternion
        if _quat != None:
            _quat_w = _quat[0] if _quat[0] != None else None
            _quat_x = _quat[1] if _quat[1] != None else None
            _quat_y = _quat[2] if _quat[2] != None else None
            _quat_z = _quat[3] if _quat[3] != None else None
            if _quat_w != None \
                    and _quat_x != None \
                    and _quat_y != None \
                    and _quat_z != None:
                _q = Quaternion(_quat_w, _quat_x, _quat_y, _quat_z)
                _orig_quat_heading = _q.degrees
                _q_yaw_pitch_roll  = _q.yaw_pitch_roll
                _q_yaw             = _q_yaw_pitch_roll[0]
                _q_pitch           = _q_yaw_pitch_roll[1]
                _q_roll            = _q_yaw_pitch_roll[2]
        
                if _orig_quat_heading < 0.0:
                    print(Fore.YELLOW+Style.BRIGHT+'HEADING+360'+Style.RESET_ALL)
                    _orig_quat_heading += 360.0

                # heading ............................................................
#               self._log.debug(Fore.BLUE + Style.NORMAL + '_quat_w={:>5.4f}, _quat_x={:>5.4f}, _quat_y={:>5.4f}, _quat_z={:>5.4f}'.format(_quat_w, _quat_x, _quat_y, _quat_z) )
                    
                if self._is_calibrated:
                    self._heading = Convert.offset_in_degrees(_orig_quat_heading, self._quat_heading_trim)
                    self._log.info(Fore.MAGENTA + 'heading:\t{:>6.2f}°\t'.format(self._heading) \
                            + Style.DIM + '(quat; orig: {:>6.2f}°; mode: {})'.format(_orig_quat_heading, self._bno_mode.name.lower()))
#                           + Fore.CYAN + 'p={:>5.4f}; r={:>5.4f}; y={:>5.4f}'.format(_q_pitch, _q_roll, _q_yaw))
                else:
                    # we don't do an update if not calibrated
                    self._log.info(Fore.MAGENTA + 'heading:\t{:>6.2f}°\t'.format(self._heading) \
                            + Fore.BLACK + Style.DIM + '(quat; UNCHANGED; mode: {})'.format(self._bno_mode.name.lower()))
        
#   #           # pitch ..............................................................
#   #           if Convert.in_range(_e_pitch, _q_pitch, self._error_range):
#   #               self._pitch = _e_pitch + self._pitch_trim
#   #               self._log.debug('    ' + Fore.CYAN     + Style.BRIGHT + 'pitch:  \t{:>5.4f}° (calibrated)'.format(_e_pitch))
#   #           else:
#   #               self._log.debug('    ' + Fore.YELLOW   + Style.BRIGHT + 'pitch:  \t{:>5.4f}° (euler)'.format(_e_pitch))
#   #               self._log.debug('    ' + Fore.GREEN    + Style.BRIGHT + 'pitch:  \t{:>5.4f}° (quaternion)'.format(_q_pitch))
#   #               self._pitch = None
#   #           # roll ...............................................................
#   #           if Convert.in_range(_e_roll, _q_roll, self._error_range):
#   #               self._roll = _e_roll + self._roll_trim
#   #               self._log.debug('    ' + Fore.CYAN     + Style.BRIGHT + 'roll:   \t{:>5.4f}° (calibrated)'.format(_e_roll))
#   #           else:
#   #               self._log.debug('    ' + Fore.YELLOW   + Style.BRIGHT + 'roll:   \t{:>5.4f}° (euler)'.format(_e_roll))
#   #               self._log.debug('    ' + Fore.GREEN    + Style.BRIGHT + 'roll:   \t{:>5.4f}° (quaternion)'.format(_q_roll))
#   #               self._roll = None
            else:
                self._log.info(Fore.BLACK + 'null quaternion components {}.'.format(_quat))

        else:
            self._log.info(Fore.BLACK + 'null quaternion.')
            pass

        self._log.debug('read ended.')
        return ( self._is_calibrated, _euler_converted_heading, self._heading )


# ..............................................................................
class BNO055Mode(Enum):
    '''
        Encapsulates the available modes of the BNO055. These constants are
        copied directly from the source at:

          /usr/local/lib/python3.7/dist-packages/adafruit_bno055.py

        No expectation that these may not change in a future version of the
        hardware or software, but this seems pretty unlikely.

        +------------------+-------+---------+------+----------+
        | Mode             | Accel | Compass | Gyro | Absolute |
        +==================+=======+=========+======+==========+
        | CONFIG_MODE      |   -   |   -     |  -   |     -    |
        +------------------+-------+---------+------+----------+
        | ACCONLY_MODE     |   X   |   -     |  -   |     -    |
        +------------------+-------+---------+------+----------+
        | MAGONLY_MODE     |   -   |   X     |  -   |     -    |
        +------------------+-------+---------+------+----------+
        | GYRONLY_MODE     |   -   |   -     |  X   |     -    |
        +------------------+-------+---------+------+----------+
        | ACCMAG_MODE      |   X   |   X     |  -   |     -    |
        +------------------+-------+---------+------+----------+
        | ACCGYRO_MODE     |   X   |   -     |  X   |     -    |
        +------------------+-------+---------+------+----------+
        | MAGGYRO_MODE     |   -   |   X     |  X   |     -    |
        +------------------+-------+---------+------+----------+
        | AMG_MODE         |   X   |   X     |  X   |     -    |
        +------------------+-------+---------+------+----------+
        | IMUPLUS_MODE     |   X   |   -     |  X   |     -    |
        +------------------+-------+---------+------+----------+
        | COMPASS_MODE     |   X   |   X     |  -   |     X    |
        +------------------+-------+---------+------+----------+
        | M4G_MODE         |   X   |   X     |  -   |     -    |
        +------------------+-------+---------+------+----------+
        | NDOF_FMC_OFF_MODE|   X   |   X     |  X   |     X    |
        +------------------+-------+---------+------+----------+
        | NDOF_MODE        |   X   |   X     |  X   |     X    |
        +------------------+-------+---------+------+----------+

        The default mode is ``NDOF_MODE``.

        | You can set the mode using the line below:
        | ``sensor.mode = adafruit_bno055.ACCONLY_MODE``
        | replacing ``ACCONLY_MODE`` with the mode you want to use

        .. data:: CONFIG_MODE

           This mode is used to configure BNO, wherein all output data is reset to zero and sensor
           fusion is halted.

        .. data:: ACCONLY_MODE

           In this mode, the BNO055 behaves like a stand-alone acceleration sensor. In this mode the
           other sensors (magnetometer, gyro) are suspended to lower the power consumption.

        .. data:: MAGONLY_MODE

           In MAGONLY mode, the BNO055 behaves like a stand-alone magnetometer, with acceleration
           sensor and gyroscope being suspended.

        .. data:: GYRONLY_MODE

           In GYROONLY mode, the BNO055 behaves like a stand-alone gyroscope, with acceleration
           sensor and magnetometer being suspended.

        .. data:: ACCMAG_MODE

           Both accelerometer and magnetometer are switched on, the user can read the data from
           these two sensors.

        .. data:: ACCGYRO_MODE

           Both accelerometer and gyroscope are switched on; the user can read the data from these
           two sensors.

        .. data:: MAGGYRO_MODE

           Both magnetometer and gyroscope are switched on, the user can read the data from these
           two sensors.

        .. data:: AMG_MODE

           All three sensors accelerometer, magnetometer and gyroscope are switched on.

        .. data:: IMUPLUS_MODE

           In the IMU mode the relative orientation of the BNO055 in space is calculated from the
           accelerometer and gyroscope data. The calculation is fast (i.e. high output data rate).

        .. data:: COMPASS_MODE

           The COMPASS mode is intended to measure the magnetic earth field and calculate the
           geographic direction.

        .. data:: M4G_MODE

           The M4G mode is similar to the IMU mode, but instead of using the gyroscope signal to
           detect rotation, the changing orientation of the magnetometer in the magnetic field is
           used.

        .. data:: NDOF_FMC_OFF_MODE

           This fusion mode is same as NDOF mode, but with the Fast Magnetometer Calibration turned
           ‘OFF’.

        .. data:: NDOF_MODE

           This is a fusion mode with 9 degrees of freedom where the fused absolute orientation data
           is calculated from accelerometer, gyroscope and the magnetometer.
    '''
    CONFIG_MODE       = (  1, adafruit_bno055.CONFIG_MODE )
    ACCONLY_MODE      = (  2, adafruit_bno055.ACCONLY_MODE )
    MAGONLY_MODE      = (  3, adafruit_bno055.MAGONLY_MODE )
    GYRONLY_MODE      = (  4, adafruit_bno055.GYRONLY_MODE )
    ACCMAG_MODE       = (  5, adafruit_bno055.ACCMAG_MODE )
    ACCGYRO_MODE      = (  6, adafruit_bno055.ACCGYRO_MODE )
    MAGGYRO_MODE      = (  7, adafruit_bno055.MAGGYRO_MODE )
    AMG_MODE          = (  8, adafruit_bno055.AMG_MODE )
    IMUPLUS_MODE      = (  9, adafruit_bno055.IMUPLUS_MODE )
    COMPASS_MODE      = ( 10, adafruit_bno055.COMPASS_MODE )
    M4G_MODE          = ( 11, adafruit_bno055.M4G_MODE )
    NDOF_FMC_OFF_MODE = ( 12, adafruit_bno055.NDOF_FMC_OFF_MODE )
    NDOF_MODE         = ( 13, adafruit_bno055.NDOF_MODE )

    # ignore the first param since it's already set by __new__
    def __init__(self, num, mode):
        self._num = num
        self._mode = mode

    # this makes sure the mode is read-only
    @property
    def mode(self):
        return self._mode

    # lookup by int value
    @staticmethod
    def from_num(value):
        for mode in BNO055Mode:
            if mode._num == value:
                return mode
        raise AttributeError('unrecognised lookup "{}" for BNO055Mode.'.format(value))

    # lookup by name
    @staticmethod
    def from_name(value):
        for mode in BNO055Mode:
            if mode.name == value:
                return mode
        raise AttributeError('unrecognised lookup "{}" for BNO055Mode.'.format(value))

# ..............................................................................
class Calibration(Enum):
    NEVER      = ( 1, "never calibrated",    False)
    LOST       = ( 2, "lost calibration",    False)
    CALIBRATED = ( 3, "calibrated",          True)

    # ignore the first param since it's already set by __new__
    def __init__(self, num, name, calibrated):
        self._num = num
        self._name = name
        self._calibrated = calibrated

    # this makes sure the name is read-only
    @property
    def name(self):
        return self._name

    # this makes sure the label is read-only
    @property
    def calibrated(self):
        return self._calibrated

#EOF
