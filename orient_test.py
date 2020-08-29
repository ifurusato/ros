#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# Copyright 2020 by Murray Altheim. All rights reserved. This file is part of
# the Robot OS project and is released under the "Apache Licence, Version 2.0".
# Please see the LICENSE file included as part of this package.
#
# author:  Murray Altheim
# created: 2020-03-16
#
#  Tests orientation using an Adafruit LSM9DS1 9-DoF board. This currently is
#  an unfinished test file. We're checking it in for potential future work.
#

import time, sys, signal, threading, board, busio, math
from enum import Enum
from colorama import init, Fore, Style
init()

from lib.enums import Heading
from lib.devnull import DevNull
from lib.logger import Level, Logger
from lib.queue import MessageQueue
from lib.bno055 import BNO055
import adafruit_lsm9ds1
from lib.player import Sound, Player
#from lib.motors import Motors

# conversion functions .........................................................

LSB = 0.48828125 #mG


def offset_angle(degrees, offset):
    d = math.degrees(math.radians(degrees) + math.radians(offset))
    if d > 360.0:
        d -= 360.0
    elif d < 0.0:
        d += 360.0
    return d


#def old_convert_to_degrees(x, y, z):
#    '''
#        Provided a x,y,z magnetometer reading returns a heading value in degrees.
#
#        source:  https://blog.digilentinc.com/how-to-convert-magnetometer-data-into-compass-heading/
#    '''
#    xGaussData = x * LSB
#    yGaussData = y * LSB
#    if xGaussData == 0.0:
#        if yGaussData < 0.0:
#            return 90.0
#        elif yGaussData >= 0.0:
#            return 0.0
#    else:
#        degrees = math.atan( yGaussData / xGaussData ) * ( 180.0 / math.pi )
#        if degrees > 360.0:
#            return degrees - 360.0
#        elif degrees < 0.0:
#            return degrees + 360.0
#        else:
#            return degrees


def convert_to_degrees(x, y, z):
    '''
        Provided a x,y,z magnetometer reading returns a heading value in degrees.

        source:  https://cdn-shop.adafruit.com/datasheets/AN203_Compass_Heading_Using_Magnetometers.pdf
    '''
    if y == 0.0:
        if x < 0.0:
            return 180.0
        elif x >= 0.0:
            return 0.0
    elif y > 0.0:
        return 90.0 - math.atan( x / y ) * ( 180.0 / math.pi )
    elif y < 0.0:
        return 270.0 - math.atan( x / y ) * ( 180.0 / math.pi )


def constrainAngle360(dta):
    '''
        Bound angle between 0 and 360.
    '''
    dta = math.fmod(dta, 2.0 * math.pi)
    if dta < 0.0:
        dta += 2.0 * math.pi
    return dta


WINDOW_SIZE = 20
R2D = 180.0 / math.pi;

def convert_to_degrees_with_accelerometer(hx, hy, hz, ax, ay, az):
    '''
        Converted from Arduino code.

        source: https://github.com/bolderflight/MPU9250/issues/33
    '''
    filtered_heading_rad = 1.0
    # normalize accelerometer and magnetometer data
    a = math.sqrt(ax * ax + ay * ay + az * az)
    ax /= a
    ay /= a
    az /= a
    h = math.sqrt(hx * hx + hy * hy + hz * hz)
    hx /= h
    hy /= h
    hz /= h
    # compute euler angles .......................
    pitch_rad = math.asin(ax)
    roll_rad = math.asin(-ay / math.cos(pitch_rad))
    yaw_rad = math.atan2(hz * math.sin(roll_rad) - hy * math.cos(roll_rad), hx * math.cos(pitch_rad) + hy * math.sin(pitch_rad) * math.sin(roll_rad) + hz * math.sin(pitch_rad) * math.cos(roll_rad))
    heading_rad = constrainAngle360(yaw_rad)
    # filtering heading ..........................
    filtered_heading_rad = (filtered_heading_rad * (WINDOW_SIZE - 1.0) + heading_rad) / WINDOW_SIZE
    # display the results ........................
    heading = heading_rad * R2D
    filtered_heading = filtered_heading_rad * R2D
    pitch = pitch_rad * R2D
    roll = roll_rad * R2D
    yaw = yaw_rad * R2D
    return heading, filtered_heading, pitch, roll, yaw 


# exception handler ............................................................
def signal_handler(signal, frame):
    print(Fore.RED + 'Ctrl-C caught: exiting...' + Style.RESET_ALL)
#    _motors.halt()
#    Motors.cancel()
    sys.stderr = DevNull()
    print(Fore.MAGENTA + 'exit.' + Style.RESET_ALL)
    sys.exit(0)



def calibrate(): # unused
    pass
#        MAX_COUNT = 25
#        # try to calibrate the BNO055
#        if _heading is None:
#            # if not calibrated, try rotating one direction
#            count = 0
#            _motors.spinPort(60.0)
#            while count < MAX_COUNT and _heading is None:
#                _heading = _bno055.get_heading()
#                count += 1
#                print(Fore.BLACK + '[{:d}] rotating counter-clockwise to calibrate...'.format(count) + Style.RESET_ALL)
#                time.sleep(0.5)
#            _motors.halt()
#            # if unsuccessful, try rotating the other direction
#            print(Fore.BLACK + 'finished rotating counter-clockwise.' + Style.RESET_ALL)
#            if _heading is None:
#                print(Fore.BLACK + 'still not calibrated: now rotating clockwise...' + Style.RESET_ALL)
#                count = 0
#                _motors.spinStarboard(80.0)
#                while count < MAX_COUNT and _heading is None:
#                    _heading = _bno055.get_heading()
#                    count += 1
#                    print(Fore.BLACK + '[{:d}] rotating clockwise to calibrate...'.format(count) + Style.RESET_ALL)
#                    time.sleep(0.5)
#                _motors.halt()
#            else:
#                print(Fore.BLACK + 'got heading value of {}.'.format(_heading) + Style.RESET_ALL)
#
#        if _heading is None:
#            print(Fore.RED + 'unable to calibrate.' + Style.RESET_ALL)
#        else:


# ..............................................................................

#_motors = Motors(None, None, Level.INFO)

def main():

    signal.signal(signal.SIGINT, signal_handler)

    _log = Logger("orient_test", Level.INFO)
    _log.info('start...')

    _player = Player(Level.INFO)
    _queue = MessageQueue(Level.INFO)

    try:
        i2c = busio.I2C(board.SCL, board.SDA)
        lsm9ds1 = adafruit_lsm9ds1.LSM9DS1_I2C(i2c)

        _bno055 = BNO055(_queue, Level.INFO)
        _bno055.enable()
        _heading = _bno055.get_heading()

        success = 0
        _log.info(Fore.RED + Style.BRIGHT + 'to calibrate, wave robot in air until it beeps...')

        while True:

            # read magnetometer...
            mag_x, mag_y, mag_z = lsm9ds1.magnetic 
            accel_x, accel_y, accel_z = lsm9ds1.acceleration
    
            degrees = convert_to_degrees(mag_x, mag_y, mag_z)
            direction = Heading.get_heading_from_degrees(degrees)
            lsm9ds1_heading, filtered_lsm9ds1_heading, roll, pitch, yaw = convert_to_degrees_with_accelerometer(mag_x, mag_y, mag_z, accel_x, accel_y, accel_z)


            _log.info(Fore.BLACK + 'LSM9DS1 heading: {:0.3f}°;\tdirection: {} (no accel);'.format(degrees, direction) + Fore.BLACK + Style.DIM \
                    + ' magnetometer (gauss):\t({0:0.3f}, {1:0.3f}, {2:0.3f})'.format(mag_x, mag_y, mag_z))
            _log.info(Fore.BLUE + 'LSM9DS1 heading: {:>5.2f}°;\traw heading: {:>5.2f}°; (with accel)'.format(filtered_lsm9ds1_heading, lsm9ds1_heading) + Fore.BLACK + Style.DIM \
                    + '\tpitch: {:>5.2f}; roll: {:>5.2f}; yaw: {:>5.2f}.'.format(pitch, roll, yaw) + Style.RESET_ALL)

            _heading = _bno055.get_heading()
            if _heading is None:
                _log.warning('heading: none')
            else:
                success += 1
#               offset = 90.0
                bno055_lsm9ds1_heading = offset_angle(degrees, filtered_lsm9ds1_heading)
                _log.info('BNO055 heading:  {:>5.4f}°;\toffset to LSM9DS1: {:>5.4f}°'.format(_heading, bno055_lsm9ds1_heading))
            if success == 4:
                _player.play(Sound.ALARM)

            print(Fore.BLACK + '.' + Style.RESET_ALL)
            time.sleep(0.5)
            # .......................................
   
    except KeyboardInterrupt:
        _log.info(Fore.RED + Style.BRIGHT + 'Ctrl-C caught: keyboard interrupt.')
        _bno055.close()
        _log.info('done.')
        sys.exit(0)

if __name__== "__main__":
    main()

#EOF
