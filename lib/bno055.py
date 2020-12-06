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

import sys, time, threading, itertools
from enum import Enum
import adafruit_bno055
from colorama import init, Fore, Style
init()

from lib.rate import Rate

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
        Reads from a BNO055 9DoF sensor. In order for this to be used by a
        Raspberry Pi you must in theory slow your I2C bus down to around
        10kHz, though if not things still seem to work. YMMV.

        Note that this has been calibrated based on the orientation of the
        BNO055 board as installed on the KR01 robot, with the dot on the
        chip (mounted horizontally) as follows:

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
    '''
    def __init__(self, config, queue, level):
        self._log = Logger("bno055", level)
        if config is None:
            raise ValueError("no configuration provided.")
        self._queue = queue

        self._config = config
        # config
        _config = self._config['ros'].get('bno055')
        self._loop_delay_sec    = _config.get('loop_delay_sec')
        _i2c_device             = _config.get('i2c_device')
        self._pitch_trim        = _config.get('pitch_trim')
        self._roll_trim         = _config.get('roll_trim')
        self._heading_trim      = _config.get('heading_trim')
        self._error_range       = 5.0 # permitted error between Euler and Quaternion (in degrees) to allow setting value, was 3.0
        self._rate              = Rate(_config.get('sample_rate')) # e.g., 20Hz

        # use `ls /dev/i2c*` to find out what i2c devices are connected
        self._bno055 = adafruit_bno055.BNO055_I2C(I2C(_i2c_device)) # Device is /dev/i2c-1
        # some of the other modes provide accurate compass calibration but are very slow to calibrate
#       self._bno055.mode = BNO055Mode.COMPASS_MODE.mode 
#       self._bno055.mode = BNO055Mode.NDOF_FMC_OFF_MODE.mode

        self._counter = itertools.count()
        self._thread  = None
        self._enabled = False
        self._closed  = False
        self._heading = 0.0    # we jauntily default at zero so we don't return a None
        self._pitch   = None
        self._roll    = None
        self._is_calibrated = Calibration.NEVER
        self._log.info('ready.')

    # ..........................................................................
    def enable(self):
        if not self._closed:
            self._enabled = True
            # if we haven't started the thread yet, do so now...
            if self._thread is None:
                self._thread = threading.Thread(target=BNO055._read, args=[self])
                self._thread.start()
                self._log.info('enabled.')
            else:
                self._log.warning('thread already exists.')
        else:
            self._log.warning('cannot enable: already closed.')

    # ..........................................................................
    def get_heading(self):
        '''
            Returns a tuple containing a Calibration (enum) indicating if the
            sensor is calibrated followed by the heading value.
        '''
        return ( self._is_calibrated, self._heading )

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
    def _read(self):
        '''
            The function that reads sensor values in a loop. This checks to see
            if the 'sys' calibration is at least 3 (True), and if the Euler and
            Quaternion values are within an error range of each other, this sets
            the class variable for heading, pitch and roll. If they aren't within
            range for more than n polls, the values revert to None.
        '''
        self._log.info('starting sensor read...')
        _e_heading, _e_pitch, _e_roll, _e_yaw, _q_heading, _q_pitch, _q_roll, _q_yaw  = [None] * 8
        _quat_w = 0
        _quat_x = 0
        _quat_y = 0
        _quat_z = 0
        _count  = 0

        # begin loop .......................................
        while self._enabled and not self._closed:

            _status = self._bno055.calibration_status
            # status: sys, gyro, accel, mag
            _sys_calibrated = ( _status[0] >= 3 )
            _gyr_calibrated = ( _status[1] >= 3 )
            _acc_calibrated = ( _status[2] >= 2 )
            _mag_calibrated = ( _status[3] >= 2 )


            # "Therefore we recommend that as long as Magnetometer is 3/3, and Gyroscope is 3/3, the data can be trusted."
            # source: https://community.bosch-sensortec.com/t5/MEMS-sensors-forum/BNO055-Calibration-Staus-not-stable/td-p/8375
            _ok_calibrated = _gyr_calibrated and _mag_calibrated

            # show calibration of each sensor
            self._log.info( Fore.MAGENTA + ( Style.BRIGHT if _sys_calibrated else Style.DIM ) + ' s{}'.format(_status[0]) \
                          + Fore.YELLOW  + ( Style.BRIGHT if _gyr_calibrated else Style.DIM ) + ' g{}'.format(_status[1]) \
                          + Fore.GREEN   + ( Style.BRIGHT if _acc_calibrated else Style.DIM ) + ' a{}'.format(_status[2]) \
                          + Fore.CYAN    + ( Style.BRIGHT if _mag_calibrated else Style.DIM ) + ' m{}'.format(_status[3]) )

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
                    _q_heading        = _q.degrees
                    _q_yaw_pitch_roll = _q.yaw_pitch_roll
                    _q_yaw            = _q_yaw_pitch_roll[0]
                    _q_pitch          = _q_yaw_pitch_roll[1]
                    _q_roll           = _q_yaw_pitch_roll[2]
        
                    time.sleep(0.5) # TEMP
                    # heading ............................................................
                    self._log.debug(Fore.BLUE + Style.NORMAL + '_quat_w={:>5.4f}, _quat_x={:>5.4f}, _quat_y={:>5.4f}, _quat_z={:>5.4f}'.format(_quat_w, _quat_x, _quat_y, _quat_z) )
                    
                    if _ok_calibrated:
                        self._heading = _q_heading + self._heading_trim
                        self._log.info(Fore.MAGENTA + 'heading={:>5.4f}\t p={:>5.4f}\t r={:>5.4f}\t y={:>5.4f}'.format(_q_heading, _q_pitch, _q_roll, _q_yaw) \
                                + Fore.CYAN + Style.DIM + '\tquat: {}'.format(_quat))
                        self._is_calibrated = Calibration.CALIBRATED
                    else:
                        self._log.info(Fore.CYAN + Style.DIM     + 'heading={:>5.4f}\t p={:>5.4f}\t r={:>5.4f}\t y={:>5.4f}'.format(_q_heading, _q_pitch, _q_roll, _q_yaw) \
                                + Fore.CYAN + Style.DIM + '\tquat: {}'.format(_quat))
                        self._is_calibrated = Calibration.LOST
        
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
                pass

            _count = next(self._counter)

            self._rate.wait()
            # end loop .....................................

        self._log.debug('read loop ended.')

    # ..........................................................................
    def disable(self):
        if self._enabled:
            self._enabled = False
            self._log.info('disabled.')
        else:
            self._log.warning('already disabled.')

    # ..........................................................................
    def close(self):
        if not self._closed:
            if self._enabled:
                self.disable()
            self._closed = True
            self._log.info('closed.')
        else:
            self._log.warning('already closed.')


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

    # this makes sure the name is read-only
    @property
    def mode(self):
        return self._mode

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
