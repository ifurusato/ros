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


    # ..........................................................................
    def __init__(self, config, queue, level):
        self._log = Logger("bno055", level)
        if config is None:
            raise ValueError("no configuration provided.")
        self._queue = queue

        self._config = config
        # config
        _config = self._config['ros'].get('bno055')
        self._quaternion_accept = _config.get('quaternion_accept') # permit Quaternion once calibrated
        self._loop_delay_sec    = _config.get('loop_delay_sec')
        _i2c_device             = _config.get('i2c_device')
        self._pitch_trim        = _config.get('pitch_trim')
        self._roll_trim         = _config.get('roll_trim')
        self._heading_trim      = _config.get('heading_trim')
        self._error_range       = 5.0 # permitted error between Euler and Quaternion (in degrees) to allow setting value, was 3.0
        self._rate              = Rate(_config.get('sample_rate')) # e.g., 20Hz

        # use `ls /dev/i2c*` to find out what i2c devices are connected
        self._bno055 = adafruit_bno055.BNO055_I2C(I2C(_i2c_device)) # Device is /dev/i2c-1

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
        _e_heading = None
        _e_pitch   = None
        _e_roll    = None
        _e_yaw     = None
        _q_heading = None
        _q_pitch   = None
        _q_roll    = None
        _q_yaw     = None
        _quat_w    = None
        _quat_x    = None
        _quat_y    = None
        _quat_z    = None
        _count     = 0

        # begin loop .......................................
        while self._enabled and not self._closed:

            _status = self._bno055.calibration_status
            # status: sys, gyro, accel, mag
            _sys_calibrated           = ( _status[0] >= 3 )
            _gyro_calibrated          = ( _status[1] >= 3 )
            _accelerometer_calibrated = ( _status[2] >= 3 )
            _magnetometer_calibrated  = ( _status[3] >= 3 )

            # "Therefore we recommend that as long as Magnetometer is 3/3, and Gyroscope is 3/3, the data can be trusted."
            # source: https://community.bosch-sensortec.com/t5/MEMS-sensors-forum/BNO055-Calibration-Staus-not-stable/td-p/8375
            _is_calibrated = _gyro_calibrated and _magnetometer_calibrated
            if _is_calibrated:
                self._log.debug('calibrated: s{}-g{}-a{}-m{}.'.format(_status[0], _status[1], _status[2], _status[3]))
            else:
                self._log.debug('not calibrated: s{}-g{}-a{}-m{}.'.format(_status[0], _status[1], _status[2], _status[3]))

#           1. Absolute Orientation (Euler Vector, 100Hz) Three axis orientation data based on a 360° sphere ...........................
            _euler = self._bno055.euler
            if _euler[0] is not None:
                _e_heading = _euler[0]
            if _euler[1] is not None:
                _e_pitch = -1.0 * _euler[1]
            if _euler[2] is not None:
                _e_roll = _euler[2]

#           2. Absolute Orientation (Quaterion, 100Hz) Four point quaternion output for more accurate data manipulation ................
            _quat = self._bno055.quaternion
            if _quat is not None:
                if _quat[0] is not None:
                    _quat_w = _quat[0]
                if _quat[1] is not None:
                    _quat_x = _quat[1]
                if _quat[2] is not None:
                    _quat_y = _quat[2]
                if _quat[3] is not None:
                    _quat_z = _quat[3]

            _sys_calibrated = True # override, just pay attention to values
            if _sys_calibrated \
                    and ( None not in (_e_heading, _e_pitch, _e_roll ) ) \
                    and ( None not in (_quat_w, _quat_x, _quat_y, _quat_z ) ):
#               _q_euler = self._convert_to_euler(_quat_w, _quat_x, _quat_y, _quat_z)
                _q = Quaternion(_quat_w, _quat_x, _quat_y, _quat_z)

                _q_heading        = _q.degrees
                _q_yaw_pitch_roll = _q.yaw_pitch_roll
                _q_yaw            = _q_yaw_pitch_roll[0]
                _q_pitch          = _q_yaw_pitch_roll[1]
                _q_roll           = _q_yaw_pitch_roll[2]

                time.sleep(0.5) # TEMP
                # heading ............................................................
                if Convert.in_range(_e_heading, _q_heading, self._error_range):
                    self._heading = _q_heading + self._heading_trim
#                   if self._heading < 0.0:
#                       self._heading = self._heading + 360.0
                    self._log.info('    ' + Fore.MAGENTA   + Style.BRIGHT + 'eh: \t {:>5.4f}° (trusted);    '.format(_e_heading) \
                            + Fore.BLACK + Style.NORMAL + '\t qh={:>5.4f}\t p={:>5.4f}\t r={:>5.4f}\t y={:>5.4f}'.format(_q_heading, _q_pitch, _q_roll, _q_yaw))
                    self._is_calibrated = Calibration.TRUSTED
                elif self._quaternion_accept: # if true, we permit Quaternion once we've achieved calibration
                    self._heading = _e_heading + self._heading_trim
#                   if self._heading < 0.0:
#                       self._heading = self._heading + 360.0
                    self._log.info('    ' + Fore.CYAN      + Style.NORMAL + 'eh: \t {:>5.4f}° (calibrated); '.format(_e_heading) \
                            + Fore.BLACK + Style.NORMAL + '\t qh={:>5.4f}\t p={:>5.4f}\t r={:>5.4f}\t y={:>5.4f}'.format(_q_heading, _q_pitch, _q_roll, _q_yaw))
                    self._is_calibrated = Calibration.CALIBRATED
                else:
#                   self._heading = None # just leave last value in place?
                    self._log.info('    ' + Fore.CYAN      + Style.DIM    + 'eh: \t {:>5.4f}° (lost);       '.format(_e_heading) \
                            + Fore.BLACK + Style.NORMAL + '\t qh={:>5.4f}\t p={:>5.4f}\t r={:>5.4f}\t y={:>5.4f}'.format(_q_heading, _q_pitch, _q_roll, _q_yaw))
                    self._is_calibrated = Calibration.LOST

#               # pitch ..............................................................
#               if Convert.in_range(_e_pitch, _q_pitch, self._error_range):
#                   self._pitch = _e_pitch + self._pitch_trim
#                   self._log.debug('    ' + Fore.CYAN     + Style.BRIGHT + 'pitch:  \t{:>5.4f}° (calibrated)'.format(_e_pitch))
#               else:
#                   self._log.debug('    ' + Fore.YELLOW   + Style.BRIGHT + 'pitch:  \t{:>5.4f}° (euler)'.format(_e_pitch))
#                   self._log.debug('    ' + Fore.GREEN    + Style.BRIGHT + 'pitch:  \t{:>5.4f}° (quaternion)'.format(_q_pitch))
#                   self._pitch = None
#               # roll ...............................................................
#               if Convert.in_range(_e_roll, _q_roll, self._error_range):
#                   self._roll = _e_roll + self._roll_trim
#                   self._log.debug('    ' + Fore.CYAN     + Style.BRIGHT + 'roll:   \t{:>5.4f}° (calibrated)'.format(_e_roll))
#               else:
#                   self._log.debug('    ' + Fore.YELLOW   + Style.BRIGHT + 'roll:   \t{:>5.4f}° (euler)'.format(_e_roll))
#                   self._log.debug('    ' + Fore.GREEN    + Style.BRIGHT + 'roll:   \t{:>5.4f}° (quaternion)'.format(_q_roll))
#                   self._roll = None

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
class Calibration(Enum):
    NEVER      = ( 1, "never calibrated",    False)
    LOST       = ( 2, "lost calibration",    False)
    CALIBRATED = ( 3, "calibrated",          True)
    TRUSTED    = ( 4, "trusted calibration", True)

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
