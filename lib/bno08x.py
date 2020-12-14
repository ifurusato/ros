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
#   https://cdn-learn.adafruit.com/downloads/pdf/adafruit-9-dof-orientation-imu-fusion-breakout-bno085.pdf
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
        PacketError,
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
        # default trim, can be overridden by methods
        self.set_heading_trim(_config.get('heading_trim'))
        self.set_pitch_trim(_config.get('pitch_trim'))
        self.set_roll_trim(_config.get('roll_trim'))
        i2c = busio.I2C(board.SCL, board.SDA, frequency=800000)
        self._bno = BNO08X_I2C(i2c, debug=False)
#       self._bno = BNO08X()
        self._error_range       = 5.0 # permitted error between Euler and Quaternion (in degrees) to allow setting value, was 3.0
        self._min_calib_status  = 1
        self._settle_sec        = 0.0
        self._calibrated        = False
        self._verbose           = False # True for stack traces
        self._configure()
        self._log.info('ready.')

    # ..........................................................................
    def set_heading_trim(self, trim):
        '''
        Set the heading trim in degrees.
        '''
        self._heading_trim = trim
        self._log.info('heading trim:\t{:>6.2f}°'.format(self._heading_trim))

    # ..........................................................................
    @property
    def heading_trim(self):
        '''
        Return the heading trim in degrees.
        '''
        return self._heading_trim

    # ..........................................................................
    def set_pitch_trim(self, trim):
        '''
        Set the pitch trim in degrees.
        '''
        self._pitch_trim = trim
        self._log.info('pitch trim:  \t{:>6.2f}°'.format(self._pitch_trim))

    # ..........................................................................
    @property
    def pitch_trim(self):
        '''
        Return the pitch trim in degrees.
        '''
        return self._pitch_trim

    # ..........................................................................
    def set_roll_trim(self, trim):
        '''
        Set the roll trim in degrees.
        '''
        self._roll_trim = trim
        self._log.info('roll trim:   \t{:>6.2f}°'.format(self._roll_trim))

    # ..........................................................................
    @property
    def roll_trim(self):
        '''
        Return the roll trim in degrees.
        '''
        return self._roll_trim

    # ..........................................................................
    def _configure(self):
        self._log.info('settle time... ({:1.0f}s)'.format(self._settle_sec))
        time.sleep(self._settle_sec) # settle before calibration
        self._log.info(Fore.YELLOW + 'begin configuration/calibration...')
        self._bno.begin_calibration()
        time.sleep(0.1)
        try:
            self._log.info(Fore.YELLOW + 'setting features...')
            _features = [
                    BNO_REPORT_ACCELEROMETER,
                    BNO_REPORT_GYROSCOPE,
                    BNO_REPORT_MAGNETOMETER,
                    BNO_REPORT_ROTATION_VECTOR,
                    BNO_REPORT_GEOMAGNETIC_ROTATION_VECTOR,
                    BNO_REPORT_STABILITY_CLASSIFIER,
                    BNO_REPORT_ACTIVITY_CLASSIFIER 
#                   BNO_REPORT_GAME_ROTATION_VECTOR,
#                   BNO_REPORT_LINEAR_ACCELERATION,
#                   BNO_REPORT_STEP_COUNTER,
#                   BNO_REPORT_SHAKE_DETECTOR,
#                   BNO_REPORT_RAW_ACCELEROMETER,
#                   BNO_REPORT_RAW_GYROSCOPE,
#                   BNO_REPORT_RAW_MAGNETOMETER,
                ]
            for feature in _features:
                self._log.debug('feature {}'.format(feature))
                self._bno.enable_feature(feature)
                time.sleep(0.01)
            self._log.info(Fore.YELLOW + 'features set.  ------------------- ')

            # now calibrate...
            self._log.info(Fore.YELLOW + 'calibrating...')
            start_time = time.monotonic()
            _fail_count = 0
            _confidence = 0
            while not self._calibrated \
                    and _confidence < 50 \
                    and _fail_count < 30:
                _fail_count += 1
                try:

                    _confidence = self._activity_report()
                    self._stability_report()
                    _calibration_status = self._calibration_report()
    
                    self._log.info("Magnetometer:")
                    mag_x, mag_y, mag_z = self._bno.magnetic  # pylint:disable=no-member
                    self._log.info("X: {:0.6f}  Y: {:0.6f} Z: {:0.6f} uT".format(mag_x, mag_y, mag_z))
    
#                   self._log.info("Game Rotation Vector Quaternion:")
#                   ( game_quat_i, game_quat_j, game_quat_k, game_quat_real,) = self._bno.game_quaternion  # pylint:disable=no-member
#                   self._log.info("I: {:0.6f}  J: {:0.6f} K: {:0.6f}  Real: {:0.6f}".format(game_quat_i, game_quat_j, game_quat_k, game_quat_real))
    
                    if _calibration_status >= self._min_calib_status: # we'll settle for Low Accuracy to start
                        self._calibrated = True
                        self._log.info(Fore.GREEN + "Calibrated.")
                        if _calibration_status > 1: # but save it if better than Low.
                            self._log.info(Fore.GREEN + Style.BRIGHT + "better than low quality calibration, saving status...")
                            self._bno.save_calibration_data()
                        break
                    time.sleep(0.2)
                except Exception as e:
                    self._log.error("calibration error: {}".format(e))
                finally:
                    self._min_calib_status = 1
                    self._calibrated = True

                self._log.info(Fore.BLACK + "fail count: {:d}".format(_fail_count))

        except Exception as e:
            self._log.error('error setting features: {}'.format(e))

        self._log.info("calibration done")

    # ..........................................................................
    @property
    def calibrated(self):
        return self._calibrated

    # ..........................................................................
    def _stability_report(self):
        '''
        Prints a report indicating the current stability status, returning 
        a text string.
        '''
        _stability_classification = self._bno.stability_classification
        self._log.info(Fore.BLUE + "Stability:  \t{}".format(_stability_classification))
        pass

    # ..........................................................................
    def _activity_report(self):
        '''
        Prints a report indicating the current activity, returning an int 
        indicating a confidence level from 0-100%.
        '''
        _activity_classification = self._bno.activity_classification
        _most_likely = _activity_classification["most_likely"]
        _confidence = _activity_classification[_most_likely]
        self._log.info(Fore.BLUE + "Activity:   \t{}".format(_most_likely))
        self._log.info(Fore.BLUE + "Confidence: \t{}%".format(_confidence))
        return _confidence

    # ..........................................................................
    def _calibration_report(self):
        '''
        Prints a report indicating the current calibration status,
        returning an int value from 0-3, as follows: "Accuracy Unreliable",
        "Low Accuracy", "Medium Accuracy", or "High Accuracy".
        '''
        _calibration_status = self._bno.calibration_status
        self._log.info(Fore.BLUE + "Calibration:\t{} ({:d})".format(REPORT_ACCURACY_STATUS[_calibration_status], _calibration_status))
        return _calibration_status

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
            self._log.info(color + 'heading: {:>6.2f}°\t({})\t'.format(_q_heading, title) + Fore.BLACK + 'p={:>5.4f}\t r={:>5.4f}\t y={:>5.4f}'.format(_q_pitch, _q_roll, _q_yaw))

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

            # reports ......................................
#           _confidence = self._activity_report()
#           self._stability_report()
#           _calibration_status = self._calibration_report()

#           if _calibration_status >= self._min_calib_status:
            if True:

                # Accelerometer ..................................................................
#               gyro_x, gyro_y, gyro_z = self._bno.gyro  # pylint:disable=no-member
#               self._log.info(Fore.RED + 'Gyroscope:\tX: {:0.6f}  Y: {:0.6f} Z: {:0.6f} rads/s'.format(gyro_x, gyro_y, gyro_z))

                # Magnetometer ...................................................................
#               self._log.info(Fore.BLACK + 'self._bno.magnetic...')
                mag_x, mag_y, mag_z = self._bno.magnetic  # pylint:disable=no-member
                _mag_degrees = Convert.convert_to_degrees(mag_x, mag_y, mag_z)
                if self._heading_trim != 0.0:
                    _mag_degrees = Convert.offset_in_degrees(_mag_degrees, self._heading_trim)
                self._log.info(Fore.YELLOW + 'heading: {:>6.2f}°\t(magneto)'.format(_mag_degrees))

                # Rotation Vector Quaternion .....................................................
#               self._log.info(Fore.BLACK + 'self._bno.quaternion...')
                ( quat_i, quat_j, quat_k, quat_real ) = self._bno.quaternion  # pylint:disable=no-member
                _quaternion = self._bno.quaternion
                self._process_quaternion(Fore.GREEN, 'rot-quat', self._bno.quaternion)

                # Geomagnetic Rotation Vector Quatnernion ........................................
#               self._log.info(Fore.BLACK + 'self._bno.geometric_quaternion...')
                _geomagnetic_quaternion = self._bno.geomagnetic_quaternion
                ( geo_quat_i, geo_quat_j, geo_quat_k, geo_quat_real, ) = _geomagnetic_quaternion  # pylint:disable=no-member
                self._process_quaternion(Fore.GREEN + Style.BRIGHT, 'geo-quat', _geomagnetic_quaternion)
                return _mag_degrees, _quaternion[0], _geomagnetic_quaternion[0]

            else:
                self._log.warning('uncalibrated...')
                return 0.0, 0.0, 0.0

            self._log.debug('read ended.')

        except KeyError as ke:
            if self._verbose:
                self._log.error('bno08x key error: {} {}'.format(ke, traceback.format_exc()))
            else:
                self._log.error('bno08x key error: {}'.format(ke))
        except RuntimeError as re:
            if self._verbose:
                self._log.error('bno08x runtime error: {} {}'.format(re, traceback.format_exc()))
            else:
                self._log.error('bno08x runtime error: {}'.format(re))
        except IndexError as ie:
            if self._verbose:
                self._log.error('bno08x index error: {} {}'.format(ie, traceback.format_exc()))
            else:
                self._log.error('bno08x index error: {}'.format(ie))
        except OSError as oe:
            if self._verbose:
                self._log.error('bno08x os error: {} {}'.format(oe, traceback.format_exc()))
            else:
                self._log.error('bno08x OS error: {}'.format(oe))
        except PacketError as pe:
            if self._verbose:
                self._log.error('bno08x packet error: {} {}'.format(pe, traceback.format_exc()))
            else:
                self._log.error('bno08x packet error: {}'.format(pe))
        except Exception as e:
            if self._verbose:
                self._log.error('bno08x error: {} {}'.format(e, traceback.format_exc()))
            else:
                self._log.error('bno08x error: {}'.format(e))

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
