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
# Support for the Adafruit 9-DOF Orientation IMU Fusion Breakout - BNO085 (BNO080).
#
# See:
#   https://www.adafruit.com/product/4754
#   https://learn.adafruit.com/adafruit-9-dof-orientation-imu-fusion-breakout-bno085
#   https://learn.adafruit.com/adafruit-9-dof-orientation-imu-fusion-breakout-bno085/report-types
#   https://www.ceva-dsp.com/wp-content/uploads/2019/10/BNO080_085-Datasheet.pdf
#   https://circuitpython.readthedocs.io/projects/bno08x/en/latest/
#

import math, sys, time, traceback
import board, busio
from enum import Enum
from colorama import init, Fore, Style
init()

# if not busio.I2C, then use this:
#try:
#    from adafruit_extended_bus import ExtendedI2C as I2C
#except ImportError as ie:
#    sys.exit("This script requires the adafruit_extended_bus module.\n"\
#           + "Install with: sudo pip3 install adafruit_extended_bus")
try:
    import adafruit_bno08x
    from adafruit_bno08x.i2c import BNO08X_I2C
#   from adafruit_bno08x.i2c import BNO08X
    from adafruit_bno08x import (
#       PacketError,
        BNO_REPORT_ACCELEROMETER,
        BNO_REPORT_GYROSCOPE,
        BNO_REPORT_MAGNETOMETER,
        BNO_REPORT_ROTATION_VECTOR,
        BNO_REPORT_GEOMAGNETIC_ROTATION_VECTOR,
        BNO_REPORT_GAME_ROTATION_VECTOR,
        REPORT_ACCURACY_STATUS,
        BNO_REPORT_ACTIVITY_CLASSIFIER,
        BNO_REPORT_STABILITY_CLASSIFIER,
    )
except ImportError as ie:
    sys.exit("This script requires the adafruit_bno08x module.\n"\
           + "Install with: sudo pip3 install adafruit-circuitpython-bno08x")
try:
    from pyquaternion import Quaternion
except ImportError:
    sys.exit("This script requires the pyquaternion module.\nInstall with: sudo pip3 install pyquaternion")

from lib.logger import Level, Logger
from lib.config_loader import ConfigLoader
from lib.message import Message
from lib.queue import MessageQueue
from lib.message_factory import MessageFactory
from lib.convert import Convert
from lib.rate import Rate

# ..............................................................................
class BNO08x:
    '''
        Reads from a BNO08x 9DoF sensor.
    '''
    def __init__(self, config, queue, level):
        self._log = Logger("bno085", level)
        if config is None:
            raise ValueError("no configuration provided.")
        self._queue = queue

        self._config = config
        # config
        _config = self._config['ros'].get('bno085')
        self._loop_delay_sec    = _config.get('loop_delay_sec')
        _i2c_device             = _config.get('i2c_device')
        self._rotate_90         = _config.get('rotate_90')
        # trim currently unused
        self._pitch_trim        = _config.get('pitch_trim')
        self._roll_trim         = _config.get('roll_trim')
        self._heading_trim      = _config.get('heading_trim')

        self._error_range       = 5.0 # permitted error between Euler and Quaternion (in degrees) to allow setting value, was 3.0
        self._rate              = Rate(_config.get('sample_rate')) # e.g., 20Hz

        i2c = busio.I2C(board.SCL, board.SDA, frequency=800000)
        self._bno = BNO08X_I2C(i2c, debug=False)
#       self._bno = BNO08X()

        self._enabled = False
        self._closed  = False
        self._log.info('ready.')

    # ..........................................................................
    def enable(self):
        if not self._closed:
            self._enabled = True
            self._log.info('enabled.')
            self._calibrate()
        else:
            self._log.warning('cannot enable: already closed.')

    # ..........................................................................
    def _calibrate(self):
        time.sleep(0.5) # settle before calibration

        try:
            self._bno.begin_calibration()
#           self._bno.enable_feature(BNO_REPORT_MAGNETOMETER)
#           self._bno.enable_feature(BNO_REPORT_GAME_ROTATION_VECTOR)

            self._bno.enable_feature(BNO_REPORT_ACCELEROMETER)
            self._bno.enable_feature(BNO_REPORT_GYROSCOPE)
            self._bno.enable_feature(BNO_REPORT_MAGNETOMETER)
            self._bno.enable_feature(BNO_REPORT_ROTATION_VECTOR)
            self._bno.enable_feature(BNO_REPORT_GEOMAGNETIC_ROTATION_VECTOR)
            self._bno.enable_feature(BNO_REPORT_GAME_ROTATION_VECTOR)
            self._bno.enable_feature(BNO_REPORT_STABILITY_CLASSIFIER)
#           self._bno.enable_feature(BNO_REPORT_ACTIVITY_CLASSIFIER)
#           self._bno.enable_feature(BNO_REPORT_LINEAR_ACCELERATION)
#           self._bno.enable_feature(BNO_REPORT_STEP_COUNTER)
#           self._bno.enable_feature(BNO_REPORT_SHAKE_DETECTOR)
#           self._bno.enable_feature(BNO_REPORT_RAW_ACCELEROMETER)
#           self._bno.enable_feature(BNO_REPORT_RAW_GYROSCOPE)
#           self._bno.enable_feature(BNO_REPORT_RAW_MAGNETOMETER)
        except Exception as e:
            self._log.error('error setting features: {}'.format(e))

        start_time = time.monotonic()
        _calibrated = None
        while True:
            try:
                _stability_classification = self._bno.stability_classification
#               self._log.info(Fore.YELLOW + "Stability Classification: {}".format(BNO_REPORT_STABILITY_CLASSIFIER[_stability_classification]))
                self._log.info(Fore.BLUE + "Stability Classification: {}.".format(_stability_classification))

                _calibration_status = self._bno.calibration_status
#               self._log.info(Fore.YELLOW + "Magnetometer Calibration quality: {}.".format(type(_calibration_status)))
                self._log.info(Fore.BLUE + "Magnetometer Calibration quality: {} ({:d})".format(REPORT_ACCURACY_STATUS[_calibration_status], _calibration_status ))

#               _activity_classification = self._bno.activity_classification
#               self._log.info(Fore.YELLOW + "Activity Classification: {}.".format(_activity_classification))

                self._log.info("Magnetometer:")
                mag_x, mag_y, mag_z = self._bno.magnetic  # pylint:disable=no-member
                self._log.info("X: {:0.6f}  Y: {:0.6f} Z: {:0.6f} uT".format(mag_x, mag_y, mag_z))

                self._log.info("Game Rotation Vector Quaternion:")
                ( game_quat_i, game_quat_j, game_quat_k, game_quat_real,) = self._bno.game_quaternion  # pylint:disable=no-member
                self._log.info("I: {:0.6f}  J: {:0.6f} K: {:0.6f}  Real: {:0.6f}".format(game_quat_i, game_quat_j, game_quat_k, game_quat_real))

                if not _calibrated and _calibration_status >= 2:
                    _calibrated = time.monotonic()
                    self._log.info(Fore.GREEN + "ALREADY CALIBRATED.  **********************************")
                    break
                if _calibrated and (time.monotonic() - _calibrated > 5.0):
                    input_str = input("\n\nEnter S to save or anything else to continue: ")
                    if input_str.strip().lower() == "s":
                        self._bno.save_calibration_data()
                        break
                    _calibrated = None
                self._log.info("**************************************************************")
                time.sleep(0.1)
            except Exception as e:
                self._log.error("calibration error: {}".format(e))

        self._log.info("calibration done")

    # ..........................................................................
    def _process_quaternion(self, color, title, quaternion):
        # ( quat_i, quat_j, quat_k, quat_real ) = self._bno.quaternion
            ( quat_i, quat_j, quat_k, quat_real ) = quaternion
            _q = Quaternion(real=quat_real, imaginary=[quat_i, quat_j, quat_k])
            _q_heading        = _q.degrees
            _q_yaw_pitch_roll = _q.yaw_pitch_roll
            _q_yaw            = _q_yaw_pitch_roll[0]
            _q_pitch          = _q_yaw_pitch_roll[1]
            _q_roll           = _q_yaw_pitch_roll[2]
            self._log.info(color + '{}\theading: {:>5.2f}°\tp={:>5.4f}\t r={:>5.4f}\t y={:>5.4f}'.format(title, _q_heading, _q_pitch, _q_roll, _q_yaw))

    # ..........................................................................
    def read(self):
        '''
            The function that reads sensor values in a loop. This checks to see
            if the 'sys' calibration is at least 3 (True), and if the Euler and
            Quaternion values are within an error range of each other, this sets
            the class variable for heading, pitch and roll. If they aren't within
            range for more than n polls, the values revert to None.
        '''
#       self._log.info('starting sensor read...')

        try:

#           self._log.info(Fore.BLACK + 'self._bno.calibration_status...')
            _calibration_status = self._bno.calibration_status
            # 0: "Accuracy Unreliable", 1: "Low Accuracy", 2: "Medium Accuracy", 3: "High Accuracy",
            if _calibration_status >= 2:

#               self._log.header('IMU Read Cycle', "Stability: {}; Calibration: {}".format(self._bno.stability_classification, REPORT_ACCURACY_STATUS[_calibration_status]), None)

#               self._log.info(Fore.BLUE + "Stability: {}; Calibration: {} ({:d})".format(self._bno.stability_classification, REPORT_ACCURACY_STATUS[_calibration_status], _calibration_status ))

                # Accelerometer ..................................................................
#               gyro_x, gyro_y, gyro_z = self._bno.gyro  # pylint:disable=no-member
#               self._log.info(Fore.RED + 'Gyroscope:\tX: {:0.6f}  Y: {:0.6f} Z: {:0.6f} rads/s'.format(gyro_x, gyro_y, gyro_z))

                # Magnetometer ...................................................................
                self._log.info(Fore.BLACK + 'self._bno.magnetic...')
                mag_x, mag_y, mag_z = self._bno.magnetic  # pylint:disable=no-member
                _mag_degrees = Convert.convert_to_degrees(mag_x, mag_y, mag_z)
                if self._rotate_90:
                    _mag_degrees = Convert.rotate_90_degrees(_mag_degrees)
                self._log.info(Fore.MAGENTA + 'mag\theading: {:>5.2f}°'.format(_mag_degrees))

                # Rotation Vector Quaternion .....................................................
                self._log.info(Fore.BLACK + 'self._bno.quaternion...')
                ( quat_i, quat_j, quat_k, quat_real ) = self._bno.quaternion  # pylint:disable=no-member
                _quaternion = self._bno.quaternion
                self._process_quaternion(Fore.GREEN, 'quat', self._bno.quaternion)

                # Geomagnetic Rotation Vector Quatnernion ........................................
                self._log.info(Fore.BLACK + 'self._bno.geometric_quaternion...')
                _geomagnetic_quaternion = self._bno.geomagnetic_quaternion
                ( geo_quat_i, geo_quat_j, geo_quat_k, geo_quat_real, ) = _geomagnetic_quaternion  # pylint:disable=no-member
                self._process_quaternion(Fore.YELLOW, 'gm-quat', _geomagnetic_quaternion)
                return _mag_degrees, _quaternion[0], _geomagnetic_quaternion[0]

            else:
                self._log.warning('uncalibrated...')
                return 0.0, 0.0, 0.0

            self._log.debug('read ended.')

#       except PacketError as e:
#           self._log.error('bno08x packet error: {}'.format(traceback.format_exc()))
        except Exception as e:
            self._log.error('bno08x error: {}'.format(e))
#           self._log.error('bno08x error: {}'.format(traceback.format_exc()))

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


## ..............................................................................
class Calibration(Enum):
    UNKNOWN    = ( 0, "Unknown", "The sensor is unable to classify the current stability.", False)
    ON_TABLE   = ( 1, "On Table", "The sensor is at rest on a stable surface with very little vibration.", False)
    STATIONARY = ( 2, "Stationary", "The sensor’s motion is below the stable threshold but the stable duration requirement has not been met. This output is only available when gyro calibration is enabled.", False)
    STABLE     = ( 3, "Stable", "The sensor’s motion has met the stable threshold and duration requirements.", True)
    IN_MOTION  = ( 4, "In motion", "The sensor is moving.", False)

    # ignore the first param since it's already set by __new__
    def __init__(self, num, name, description, calibrated):
        self._num = num
        self._name = name
        self._description = description
        self._calibrated = calibrated

    @property
    def name(self):
        return self._name

    @property
    def description(self):
        return self._description

    @property
    def calibrated(self):
        return self._calibrated

#EOF
