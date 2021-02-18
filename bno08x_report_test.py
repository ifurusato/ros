#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# SPDX-FileCopyrightText: 2020 Bryan Siepert, written for Adafruit Industries
#
# SPDX-License-Identifier: MIT
import sys, time, board, busio, traceback
import adafruit_bno08x
from adafruit_bno08x.i2c import BNO08X_I2C
from colorama import init, Fore, Style
init()

from lib.logger import Logger, Level

# --------------------------------------

_log = Logger("test", Level.INFO)

i2c = busio.I2C(board.SCL, board.SDA, frequency=800000)
bno = BNO08X_I2C(i2c)

ENABLE_ACCELEROMETER               = False
ENABLE_GYROSCOPE                   = False
ENABLE_MAGNETOMETER                = False
ENABLE_LINEAR_ACCELERATION         = False
ENABLE_ROTATION_VECTOR             = True
ENABLE_GEOMAGNETIC_ROTATION_VECTOR = True
ENABLE_GAME_ROTATION_VECTOR        = True
ENABLE_STEP_COUNTER                = False
ENABLE_STABILITY_CLASSIFIER        = True
ENABLE_ACTIVITY_CLASSIFIER         = True
ENABLE_SHAKE_DETECTOR              = False
ENABLE_RAW_ACCELEROMETER           = False
ENABLE_RAW_GYROSCOPE               = False
ENABLE_RAW_MAGNETOMETER            = False

try:

    count = 0
    bno.begin_calibration()
    time.sleep(0.01)
    _features = [
#            adafruit_bno08x.BNO_REPORT_ACCELEROMETER,
#            adafruit_bno08x.BNO_REPORT_GYROSCOPE,
#            adafruit_bno08x.BNO_REPORT_MAGNETOMETER,
#            adafruit_bno08x.BNO_REPORT_LINEAR_ACCELERATION,
             adafruit_bno08x.BNO_REPORT_ROTATION_VECTOR,
             adafruit_bno08x.BNO_REPORT_GEOMAGNETIC_ROTATION_VECTOR,
             adafruit_bno08x.BNO_REPORT_GAME_ROTATION_VECTOR,
#            adafruit_bno08x.BNO_REPORT_STEP_COUNTER,
             adafruit_bno08x.BNO_REPORT_STABILITY_CLASSIFIER,
             adafruit_bno08x.BNO_REPORT_ACTIVITY_CLASSIFIER,
#            adafruit_bno08x.BNO_REPORT_SHAKE_DETECTOR,
#            adafruit_bno08x.BNO_REPORT_RAW_ACCELEROMETER,
#            adafruit_bno08x.BNO_REPORT_RAW_GYROSCOPE,
#            adafruit_bno08x.BNO_REPORT_RAW_MAGNETOMETER
        ]
    for feature in _features:
        count += 1
        _log.info(Fore.YELLOW + '{}; enabling feature: {}'.format(count, feature))
        bno.enable_feature(feature)
        time.sleep(0.02)

    _log.info(Fore.YELLOW + 'ready: enabled {:d} features.'.format(count))

except Exception as e:
    _log.error('error enabling feature: {}'.format(e))
    sys.exit(1)


_enabled = 0
_log.heading('features enabled', 'starting loop...', '[{:d}/14]'.format(_enabled) )


while True:

    time.sleep(0.1)
    try:

        if ENABLE_ACCELEROMETER:
            accel_x, accel_y, accel_z = bno.acceleration  # pylint:disable=no-member
            _log.heading('acceleration', \
                    'X: {:0.6f}  Y: {:0.6f} Z: {:0.6f}  m/s^2'.format(accel_x, accel_y, accel_z), \
                    '[{:d}/14]'.format(_enabled))
            print("")
    
        if ENABLE_GYROSCOPE:
            gyro_x, gyro_y, gyro_z = bno.gyro  # pylint:disable=no-member
            _log.heading('gyroscope', \
                    'X: {:0.6f}  Y: {:0.6f} Z: {:0.6f} rads/s'.format(gyro_x, gyro_y, gyro_z), \
                    '[{:d}/14]'.format(_enabled))
            print("")
    
        if ENABLE_MAGNETOMETER:
            _log.info("Magnetometer:")
            mag_x, mag_y, mag_z = bno.magnetic  # pylint:disable=no-member
            _log.info("X: {:0.6f}  Y: {:0.6f} Z: {:0.6f} uT".format(mag_x, mag_y, mag_z))
            print("")
    
        if ENABLE_LINEAR_ACCELERATION:
            _log.info("Linear Acceleration:")
            ( linear_accel_x, linear_accel_y, linear_accel_z,) = bno.linear_acceleration  # pylint:disable=no-member
            _log.info("X: {:0.6f}  Y: {:0.6f} Z: {:0.6f} m/s^2".format(linear_accel_x, linear_accel_y, linear_accel_z))
            print("")
    
        if ENABLE_ROTATION_VECTOR:
            quat_i, quat_j, quat_k, quat_real = bno.quaternion  # pylint:disable=no-member
            _log.heading('rotation vector quaternion', \
                    'I: {:0.6f}  J: {:0.6f} K: {:0.6f}  Real: {:0.6f}'.format(quat_i, quat_j, quat_k, quat_real), \
                    '[{:d}/14]'.format(_enabled))
            print("")
    
        if ENABLE_GEOMAGNETIC_ROTATION_VECTOR:
            (geo_quat_i, geo_quat_j, geo_quat_k, geo_quat_real) = bno.geomagnetic_quaternion  # pylint:disable=no-member
            _log.heading('geomagnetic rotation vector quaternion', \
                    'I: {:0.6f}  J: {:0.6f} K: {:0.6f}  Real: {:0.6f}'.format(geo_quat_i, geo_quat_j, geo_quat_k, geo_quat_real), \
                    '[{:d}/14]'.format(_enabled))
            print("")
    
        if ENABLE_GAME_ROTATION_VECTOR:
            _log.info("Game Rotation Vector Quaternion:")
            ( game_quat_i, game_quat_j, game_quat_k, game_quat_real,) = bno.game_quaternion  # pylint:disable=no-member
            _log.info( "I: {:0.6f}  J: {:0.6f} K: {:0.6f}  Real: {:0.6f}".format(game_quat_i, game_quat_j, game_quat_k, game_quat_real))
            print("")
    
        if ENABLE_STEP_COUNTER:
            _log.info("Steps detected: {:d}".format(bno.steps))
            print("")
    
        if ENABLE_STABILITY_CLASSIFIER:
            _log.heading('stability classification', \
                    'stability classification: {}'.format(bno.stability_classification), \
                    '[{:d}/14]'.format(_enabled))
            print("")
    
        if ENABLE_ACTIVITY_CLASSIFIER:
            activity_classification = bno.activity_classification
            most_likely = activity_classification["most_likely"]
            _log.info("Activity classification: {}".format(most_likely) + " confidence: {:d}/100".format(activity_classification[most_likely]))
            print("")
    
        if ENABLE_RAW_ACCELEROMETER:
            (raw_accel_x, raw_accel_y, raw_accel_z,) = bno.raw_acceleration
            _log.heading('raw acceleration', \
                    'X: 0x{0:04X}  Y: 0x{1:04X} Z: 0x{2:04X} LSB'.format(raw_accel_x, raw_accel_y, raw_accel_z), \
                    '[{:d}/14]'.format(_enabled))
            print("")
    
        if ENABLE_RAW_GYROSCOPE:
            (raw_accel_x, raw_accel_y, raw_accel_z,) = bno.raw_gyro
            _log.heading('raw gyroscope', \
                    'X: 0x{0:04X}  Y: 0x{1:04X} Z: 0x{2:04X} LSB'.format(raw_accel_x, raw_accel_y, raw_accel_z), \
                    '[{:d}/14]'.format(_enabled))
            print("")
    
        if ENABLE_RAW_MAGNETOMETER:
            (raw_mag_x, raw_mag_y, raw_mag_z,) = bno.raw_magnetic
            _log.heading('raw magnetometer', \
                    'X: 0x{0:04X}  Y: 0x{1:04X} Z: 0x{2:04X} LSB'.format(raw_mag_x, raw_mag_y, raw_mag_z), \
                    '[{:d}/14]'.format(_enabled))
            print("")
    
        if ENABLE_SHAKE_DETECTOR:
            if bno.shake:
                _log.warning("SHAKE DETECTED!")
            print("")

        _log.info(Fore.BLUE + "-----------------------------< end of loop >----------------------------\n") 
        time.sleep(0.5)

    except Exception as e:
        _log.error('error executing report: {}'.format(e, traceback.format_exc()))


