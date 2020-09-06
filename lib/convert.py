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
#  A class containing some static IMU-related conversion methods.
#

import numpy, math

# ..............................................................................
class Convert:

    # ..........................................................................
    @staticmethod
    def to_degrees(radians):
        return math.degrees(radians)

    # ..........................................................................
    @staticmethod
    def to_radians(degrees):
        return math.radians(degrees)

    # ..........................................................................
    @staticmethod
    def rps_to_dps(rps):
        return rps * 57.29578 

    # ..........................................................................
    @staticmethod
    def quaternion_to_euler_angle(w, x, y, z):
        q = Quaternion(w, x, y, z)
        deg = q.degrees
        return deg

    # ..........................................................................
    @staticmethod
    def quaternion_to_euler(w, x, y, z):
        t0 = +2.0 * (w * x + y * z)
        t1 = +1.0 - 2.0 * (x * x + y * y)
        roll = math.atan2(t0, t1)
        t2 = +2.0 * (w * y - z * x)
        t2 = +1.0 if t2 > +1.0 else t2
        t2 = -1.0 if t2 < -1.0 else t2
        pitch = math.asin(t2)
        t3 = +2.0 * (w * z + x * y)
        t4 = +1.0 - 2.0 * (y * y + z * z)
        heading = math.atan2(t3, t4)
        return [heading, pitch, roll]

    # ..........................................................................
    @staticmethod
    def quaternion_to_euler_angle_other(w, x, y, z):
        ysqr = y * y
        t0 = +2.0 * (w * x + y * z)
        t1 = +1.0 - 2.0 * (x * x + ysqr)
        X = numpy.degrees(numpy.arctan2(t0, t1))
        t2 = +2.0 * (w * y - z * x)
        t2 = numpy.clip(t2, a_min=-1.0, a_max=1.0)
        Y = numpy.degrees(numpy.arcsin(t2))
        t3 = +2.0 * (w * z + x * y)
        t4 = +1.0 - 2.0 * (ysqr + z * z)
        Z = numpy.degrees(numpy.arctan2(t3, t4))
        return X, Y, Z

    # ..........................................................................
    @staticmethod
    def convert_to_euler(qw, qx, qy, qz):
        # can get the euler angles back out in degrees (set to True)
        _euler = quat2euler(qw, qx, qy, qz, degrees=True)
        _heading = -1.0 * _euler[2]
        _pitch   = _euler[1]
        _roll    = -1.0 * _euler[0]
        return [ _heading, _pitch, _roll ]

    # ..........................................................................
    @staticmethod
    def in_range(p, q, error_range):
        '''
            Returns True if the first two numbers are within the supplied range
            of each other.
        '''
        return p >= ( q - error_range ) and p <= ( q + error_range )

# EOF
