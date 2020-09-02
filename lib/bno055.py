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

import sys, time, numpy, math, board, busio, threading
from colorama import init, Fore, Style
init()

from math import sin, cos, atan2, pi, sqrt # used for nxp-imu code

import adafruit_bno055

try:
    from adafruit_extended_bus import ExtendedI2C as I2C
except ImportError as ie:
    print(Fore.RED + 'unable to import adafruit_extended_bus: {}'.format(ie))
    sys.exit("This script requires the adafruit-circuitpython-register and adafruit-circuitpython-busdevice modules.\n"\
           + "Install with: sudo pip3 install adafruit-circuitpython-register adafruit-circuitpython-busdevice")

#try:
#    from nxp_imu import IMU
#except ImportError as ie:
#    print(Fore.RED + 'unable to import nxp-imu: {}'.format(ie))
#    sys.exit("This script requires the nxp-imu module.\n"\
#           + "Install with: sudo pip3 install nxp-imu")

#from squaternion import quat2euler
try:
    from pyquaternion import Quaternion
except ImportError:
    sys.exit("This script requires the pyquaternion module.\nInstall with: sudo pip3 install pyquaternion")

from lib.logger import Level, Logger
from lib.message import Message

class BNO055:
    '''
        Reads from a BNO055 9DoF sensor. In order for this to be used by a
        Raspberry Pi you must in theory slow your I2C bus down to around
        10kHz, though I've not done this and things still seem to work.

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

    # permitted error between Euler and Quaternion (in degrees) to allow setting value
    ERROR_RANGE = 5.0  # was 3.0

    # ..........................................................................
    def __init__(self, config, queue, level):
        self._log = Logger("bno055", level)
        if config is None:
            raise ValueError("no configuration provided.")
        self._config = config
        self._queue = queue

#       # verbose will print some start-up info on the IMU sensors
#       self._imu = IMU(gs=4, dps=2000, verbose=True)
#       # setting a bias correction for the accel only; the mags/gyros are not getting a bias correction
#       self._imu.setBias((0.1,-0.02,.25), None, None)

        _config = self._config['ros'].get('bno055')
        self._quaternion_accept = _config.get('quaternion_accept') # permit Quaternion once calibrated
        self._loop_delay_sec    = _config.get('loop_delay_sec')
        _i2c_device             = _config.get('i2c_device')
        self._pitch_trim        = _config.get('pitch_trim')
        self._roll_trim         = _config.get('roll_trim')
        self._heading_trim      = _config.get('heading_trim')

        # use `ls /dev/i2c*` to find out what i2c devices are connected
        self._bno055 = adafruit_bno055.BNO055_I2C(I2C(_i2c_device)) # Device is /dev/i2c-1

        self._thread  = None
        self._enabled = False
        self._closed  = False
        self._heading = None
        self._pitch   = None
        self._roll    = None
        self._is_calibrated = False
        self._h_max = 3.3 # TEMP
        self._h_min = 3.3 # TEMP
        self._log.info('ready.')

#   # ..........................................................................
#   def get_imu(self):
#       return self._imu

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
            self._log.warning('cannot enable: already closed.')

    # ..........................................................................
    def to_degrees(self, radians):
        return math.degrees(radians)

    # ..........................................................................
    def to_radians(self, degrees):
        return math.radians(degrees)

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
    def _quaternion_to_euler_angle(self, w, x, y, z):
        '''
            Returns the Quaternion calculated from the w,x,y,z coordinates.
        '''
        q = Quaternion(w, x, y, z)
        self._log.debug(Fore.BLUE + 'w={:>6.2f}\tx={:>6.2f}\ty={:>6.2f}\tz={:>6.2f}\t'.format(w, x, y, z) + Style.BRIGHT + '{:>6.2f}°'.format(q.degrees))
        return q

    # ..........................................................................
#   def _quaternion_to_euler_angle_other(self, w, x, y, z):
#       ysqr = y * y
#       t0 = +2.0 * (w * x + y * z)
#       t1 = +1.0 - 2.0 * (x * x + ysqr)
#       X = numpy.degrees(numpy.arctan2(t0, t1))
#       t2 = +2.0 * (w * y - z * x)
#       t2 = numpy.clip(t2, a_min=-1.0, a_max=1.0)
#       Y = numpy.degrees(numpy.arcsin(t2))
#       t3 = +2.0 * (w * z + x * y)
#       t4 = +1.0 - 2.0 * (ysqr + z * z)
#       Z = numpy.degrees(numpy.arctan2(t3, t4))
#       return X, Y, Z

    # ..........................................................................
#   def _quaternion_to_euler(self, w, x, y, z):
#       t0 = +2.0 * (w * x + y * z)
#       t1 = +1.0 - 2.0 * (x * x + y * y)
#       roll = math.atan2(t0, t1)
#       t2 = +2.0 * (w * y - z * x)
#       t2 = +1.0 if t2 > +1.0 else t2
#       t2 = -1.0 if t2 < -1.0 else t2
#       pitch = math.asin(t2)
#       t3 = +2.0 * (w * z + x * y)
#       t4 = +1.0 - 2.0 * (y * y + z * z)
#       heading = math.atan2(t3, t4)
#       return [heading, pitch, roll]

    # ..........................................................................
#   def _convert_to_euler(self, qw, qx, qy, qz):
#       # can get the euler angles back out in degrees (set to True)
#       _euler = quat2euler(qw, qx, qy, qz, degrees=True)
#       _heading = -1.0 * _euler[2]
#       _pitch   = _euler[1]
#       _roll    = -1.0 * _euler[0]
#       return [ _heading, _pitch, _roll ]

    # ..........................................................................
    @staticmethod
    def _in_range(p, q):
        return p >= ( q - BNO055.ERROR_RANGE ) and p <= ( q + BNO055.ERROR_RANGE )

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
        count = 0
#               2. Absolute Orientation (Quaterion, 100Hz) Four point quaternion output for more accurate data manipulation ................
        while not self._closed:
            if self._enabled:

                _status = self._bno055.calibration_status
                # status: sys, gyro, accel, mag
                _sys_calibrated           = ( _status[0] >= 3 )
                _gyro_calibrated          = ( _status[1] >= 3 )
                _accelerometer_calibrated = ( _status[2] >= 3 )
                _magnetometer_calibrated  = ( _status[3] >= 3 )

                # "Therefore we recommend that as long as Magnetometer is 3/3, and Gyroscope is 3/3, the data can be trusted."
                # source: https://community.bosch-sensortec.com/t5/MEMS-sensors-forum/BNO055-Calibration-Staus-not-stable/td-p/8375
                self._is_calibrated = _gyro_calibrated and _magnetometer_calibrated
#               self._is_calibrated = self._bno055.calibrated
                if self._is_calibrated:
                    self._log.debug('calibrated: s{}-g{}-a{}-m{}.'.format(_status[0], _status[1], _status[2], _status[3]))
                else:
                    self._log.debug('not calibrated: s{}-g{}-a{}-m{}.'.format(_status[0], _status[1], _status[2], _status[3]))

#               1. Absolute Orientation (Euler Vector, 100Hz) Three axis orientation data based on a 360° sphere ...........................
                _euler = self._bno055.euler
                if _euler[0] is not None:
                    _e_heading = _euler[0]
                if _euler[1] is not None:
                    _e_pitch = -1.0 * _euler[1]
                if _euler[2] is not None:
                    _e_roll = _euler[2]

#               2. Absolute Orientation (Quaterion, 100Hz) Four point quaternion output for more accurate data manipulation ................
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
#                   _q_euler = self._convert_to_euler(_quat_w, _quat_x, _quat_y, _quat_z)
                    _q = self._quaternion_to_euler_angle(_quat_w, _quat_x, _quat_y, _quat_z)

                    _q_yaw_pitch_roll = _q.yaw_pitch_roll
                    _q_heading        = _q.degrees
                    _q_yaw            = _q_yaw_pitch_roll[0]
                    _q_pitch          = _q_yaw_pitch_roll[1]
                    _q_roll           = _q_yaw_pitch_roll[2]

                    time.sleep(0.5) # TEMP
                    # heading ............................................................
                    if BNO055._in_range(_e_heading, _q_heading):
                        self._heading = _q_heading + self._heading_trim
                        self._log.info('    ' + Fore.MAGENTA   + Style.BRIGHT + 'eh: \t {:>5.4f}° (cal);  '.format(_e_heading) \
                                + Fore.BLACK + Style.NORMAL + '\t qh={:>5.4f}\t p={:>5.4f}\t r={:>5.4f}\t y={:>5.4f}'.format(_q_heading, _q_pitch, _q_roll, _q_yaw))
                    elif self._quaternion_accept: # if true, we permit Quaternion once we've achieved calibration
                        self._heading = _e_heading + self._heading_trim
                        self._log.info('    ' + Fore.CYAN      + Style.NORMAL + 'eh: \t {:>5.4f}° (qua);  '.format(_e_heading) \
                                + Fore.BLACK + Style.NORMAL + '\t qh={:>5.4f}\t p={:>5.4f}\t r={:>5.4f}\t y={:>5.4f}'.format(_q_heading, _q_pitch, _q_roll, _q_yaw))
                    else:
                        self._log.info('    ' + Fore.CYAN      + Style.DIM    + 'eh: \t {:>5.4f}° (non);  '.format(_e_heading) \
                                + Fore.BLACK + Style.NORMAL + '\t qh={:>5.4f}\t p={:>5.4f}\t r={:>5.4f}\t y={:>5.4f}'.format(_q_heading, _q_pitch, _q_roll, _q_yaw))
                        self._heading = None

                    # pitch ..............................................................
                    if BNO055._in_range(_e_pitch, _q_pitch):
                        self._pitch = _e_pitch + self._pitch_trim
                        self._log.debug('    ' + Fore.CYAN     + Style.BRIGHT + 'pitch:  \t{:>5.4f}° (calibrated)'.format(_e_pitch))
                    else:
                        self._log.debug('    ' + Fore.YELLOW   + Style.BRIGHT + 'pitch:  \t{:>5.4f}° (euler)'.format(_e_pitch))
                        self._log.debug('    ' + Fore.GREEN    + Style.BRIGHT + 'pitch:  \t{:>5.4f}° (quaternion)'.format(_q_pitch))
                        self._pitch = None
                    # roll ...............................................................
                    if BNO055._in_range(_e_roll, _q_roll):
                        self._roll = _e_roll + self._roll_trim
                        self._log.debug('    ' + Fore.CYAN     + Style.BRIGHT + 'roll:   \t{:>5.4f}° (calibrated)'.format(_e_roll))
                    else:
                        self._log.debug('    ' + Fore.YELLOW   + Style.BRIGHT + 'roll:   \t{:>5.4f}° (euler)'.format(_e_roll))
                        self._log.debug('    ' + Fore.GREEN    + Style.BRIGHT + 'roll:   \t{:>5.4f}° (quaternion)'.format(_q_roll))
                        self._roll = None

#               3. Angular Velocity Vector (20Hz) Three axis of 'rotation speed' in rad/s ..................................................
#               _gyro = self._bno055.gyro
#               self._log.info('    ' + Fore.YELLOW  + Style.BRIGHT + 'gyroscope 0: \t{:>5.4f} rad/sec'.format(_gyro[0]))
#               self._log.info('    ' + Fore.YELLOW  + Style.BRIGHT + 'gyroscope 1: \t{:>5.4f} rad/sec'.format(_gyro[1]))
#               self._log.info('    ' + Fore.YELLOW  + Style.BRIGHT + 'gyroscope 2: \t{:>5.4f} rad/sec'.format(_gyro[2]))

#               4. Acceleration Vector (100Hz) Three axis of acceleration (gravity + linear motion) in m/s^2 ...............................
                _accel = self._bno055.acceleration
#               self._log.info('    ' + Fore.MAGENTA + Style.BRIGHT + 'accelerometer (m/s^2): {}'.format(_accel))

#               5. Magnetic Field Strength Vector (100Hz) Three axis of magnetic field sensing in micro Tesla (uT) .........................
                _magneto = self._bno055.magnetic
#               self._log.info('    ' + Fore.RED   + Style.BRIGHT + 'magnetometer 0:\t{:>5.2f} microteslas'.format(_magneto[0]))
#               self._log.info('    ' + Fore.GREEN + Style.BRIGHT + 'magnetometer 1:\t{:>5.2f} microteslas'.format(_magneto[1]))
#               self._log.info('    ' + Fore.BLUE  + Style.BRIGHT + 'magnetometer 2:\t{:>5.2f} microteslas'.format(_magneto[2]))

                r, p, h = self.getOrientation(_accel, _magneto)
                deg = self.to_degrees(h)
                # 2pi = 6.283185307
                if h > self._h_max:
                    self._h_max = h
                if h < self._h_min:
                    self._h_min = h

                self._log.debug(Fore.CYAN + Style.BRIGHT + 'pitch/roll/heading: {:>6.3f};\t{:>6.3f}'.format(p, r) \
                        + Fore.MAGENTA + '\t{:>6.3f}rad\t{:>6.3f}°'.format(h, deg) + Fore.BLACK + '\t({:>6.3f}->{:>6.3f})'.format(self._h_min, self._h_max))

#               6. Linear Acceleration Vector (100Hz) Three axis of linear acceleration data (acceleration minus gravity) in m/s^2 .........
#               self._log.info('    ' + Fore.BLUE    + Style.BRIGHT + 'linear acceleration (m/s^2): {}'.format(self._bno055.linear_acceleration))
#               7. Gravity Vector (100Hz) Three axis of gravitational acceleration (minus any movement) in m/s^2 ...........................
#               self._log.info('    ' + Fore.WHITE   + Style.BRIGHT + 'gravity (m/s^2): {}\n'.format(self._bno055.gravity))
#               8. Temperature (1Hz) Ambient temperature in degrees celsius ................................................................
#               self._log.info('    ' + Fore.MAGENTA + Style.BRIGHT + 'temperature: {} degrees C'.format(self._bno055.temperature))

                time.sleep(self._loop_delay_sec)
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


    # math stuff from nxp-imu ..................................................

    def getOrientation(self, accel, mag, deg=False):
        """
        From AN4248.pdf
        roll: eqn 13
        pitch: eqn 15
        heading: eqn 22

        Args with biases removed:
            accel: g's
            mag: uT

        Return:
            roll, pitch, heading
        """
        ax, ay, az = self.normalize(*accel)
        mx, my, mz = self.normalize(*mag)

        roll = atan2(ay, az)
        pitch = atan2(-ax, ay*sin(roll)+az*cos(roll))
        heading = atan2(
            mz*sin(roll) - my*cos(roll),
            mx*cos(pitch) + my*sin(pitch)*sin(roll) + mz*sin(pitch)*cos(roll)
        )

#         heading = heading if heading >= 0.0 else 2*pi + heading
#         heading = heading if heading <= 2*pi else heading - 2*pi
        heading %= (2*pi)

        if deg:
            r2d = 180/pi
            roll *= r2d
            pitch *= r2d
            heading *= r2d

        return (roll, pitch, heading,)

    def normalize(self, x, y, z):
        """Return a unit vector"""
        norm = sqrt(x * x + y * y + z * z)
        if norm > 0.0:
            inorm = 1/norm
            x *= inorm
            y *= inorm
            z *= inorm
        else:
            raise Exception('division by zero: {} {} {}'.format(x, y, z))
        return (x, y, z)


#EOF
