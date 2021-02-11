#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# Copyright 2020 by Murray Altheim. All rights reserved. This file is part of
# the Robot OS project and is released under the "Apache Licence, Version 2.0".
# Please see the LICENSE file included as part of this package.
#
#    A collection of enums.
#
# author:   Murray Altheim
# created:  2019-12-23
# modified: 2020-03-26

from enum import Enum

# ..............................................................................
class Orientation(Enum):
    NONE  = ( 0, "none", "none")
    BOTH  = ( 1, "both", "both")
    PORT  = ( 2, "port", "port")
    CNTR  = ( 3, "center", "cntr")
    STBD  = ( 4, "starboard", "stbd")
    PORT_SIDE = ( 5, "port-side", "psid") # only used with infrareds
    STBD_SIDE = ( 6, "stbd-side", "ssid") # only used with infrareds

    # ignore the first param since it's already set by __new__
    def __init__(self, num, name, label):
        self._name = name
        self._label = label

    # this makes sure the name is read-only
    @property
    def name(self):
        return self._name

    # this makes sure the label is read-only
    @property
    def label(self):
        return self._label


# ..............................................................................
class Direction(Enum):
    FORWARD = 0
    REVERSE = 1


# ..............................................................................
class Color(Enum):
    WHITE          = (  1, 255.0, 255.0, 255.0)
    LIGHT_GREY     = (  2, 192.0, 192.0, 192.0)
    GREY           = (  3, 128.0, 128.0, 128.0)
    DARK_GREY      = (  4, 64.0, 64.0, 64.0)
    VERY_DARK_GREY = (  5, 32.0, 32.0, 32.0)
    BLACK          = (  6, 0.0, 0.0, 0.0)
    LIGHT_RED      = (  7, 255.0, 128.0, 128.0)
    RED            = (  8, 255.0, 0.0, 0.0)
    DARK_RED       = (  9, 128.0, 0.0, 0.0)
    ORANGE         = ( 10, 255.0, 50.0, 0.0)
#   ORANGE         = ( 10, 255.0, 128.0, 0.0)
    YELLOW_GREEN   = ( 11, 180.0, 255.0, 0.0)
    LIGHT_GREEN    = ( 12, 128.0, 255.0, 128.0)
    GREEN          = ( 13, 0.0, 255.0, 0.0)
    DARK_GREEN     = ( 14, 0.0, 128.0, 0.0)
    LIGHT_BLUE     = ( 15, 128.0, 128.0, 255.0)
    BLUE           = ( 16, 0.0, 0.0, 255.0)
    DARK_BLUE      = ( 17, 0.0, 0.0, 128.0)
    LIGHT_CYAN     = ( 18, 128.0, 255.0, 255.0)
    CYAN           = ( 19, 0.0, 255.0, 255.0)
    DARK_CYAN      = ( 20, 0.0, 128.0, 128.0)
    LIGHT_MAGENTA  = ( 21, 255.0, 128.0, 255.0)
    MAGENTA        = ( 22, 255.0, 0.0, 255.0)
    DARK_MAGENTA   = ( 23, 128.0, 0.0, 128.0)
    LIGHT_YELLOW   = ( 24, 255.0, 255.0, 128.0)
    PURPLE         = ( 25, 77.0, 26.0, 177.0)
#   YELLOW         = ( 25, 255.0, 208.0, 0.0)
    YELLOW         = ( 25, 255.0, 140.0, 0.0)
    DARK_YELLOW    = ( 27, 128.0, 128.0, 0.0)

    # ignore the first param since it's already set by __new__
    def __init__(self, num, red, green, blue):
        self._red = red
        self._green = green
        self._blue = blue

    @property
    def red(self):
        return self._red

    @property
    def green(self):
        return self._green

    @property
    def blue(self):
        return self._blue

# ..............................................................................
class Rotation(Enum):
    COUNTER_CLOCKWISE = 0
    CLOCKWISE         = 1

# ..............................................................................
class Speed(Enum): # deprecated
    STOPPED       =  0.0
    DEAD_SLOW     = 20.0
    SLOW          = 30.0
    HALF          = 50.0
    TWO_THIRDS    = 66.0
    THREE_QUARTER = 75.0
    FULL          = 90.0
    EMERGENCY     = 100.0
    MAXIMUM       = 100.000001


## ..............................................................................
#class Velocity(Enum):
#    STOP          = ( 1,  0.0 )
#    DEAD_SLOW     = ( 2, 20.0 )
#    SLOW          = ( 3, 30.0 )
#    HALF          = ( 4, 50.0 )
#    TWO_THIRDS    = ( 5, 66.7 )
#    THREE_QUARTER = ( 6, 75.0 )
#    FULL          = ( 7, 90.0 )
#    EMERGENCY     = ( 8, 100.0 )
#    MAXIMUM       = ( 9, 100.000001 )
#
#    # ignore the first param since it's already set by __new__
#    def __init__(self, num, value):
#        self._value = value
#
#    @property
#    def value(self):
#        return self._value
#
#    @staticmethod
#    def get_slower_than(velocity):
#        '''
#            Provided a value between 0-100, return the next lower Velocity.
#        '''
#        if velocity < Velocity.DEAD_SLOW.value:
#            return Velocity.STOP
#        elif velocity < Velocity.SLOW.value:
#            return Velocity.DEAD_SLOW
#        elif velocity < Velocity.HALF.value:
#            return Velocity.SLOW
#        elif velocity < Velocity.TWO_THIRDS.value:
#            return Velocity.HALF
#        elif velocity < Velocity.THREE_QUARTER.value:
#            return Velocity.TWO_THIRDS
#        elif velocity < Velocity.FULL.value:
#            return Velocity.THREE_QUARTER
#        else:
#            return Velocity.FULL

# ..............................................................................
class Cardinal(Enum):
    NORTH     = ( 0, 'north' )
    NORTHEAST = ( 1, 'north-east' )
    EAST      = ( 2, 'east' )
    SOUTHEAST = ( 3, 'south-east' )
    SOUTH     = ( 4, 'south' )
    SOUTHWEST = ( 5, 'south-west' )
    WEST      = ( 6, 'west' )
    NORTHWEST = ( 7, 'north-west' )

    # ignore the first param since it's already set by __new__
    def __init__(self, num, display):
        self._display = display

    @property
    def display(self):
        return self._display

    @staticmethod
    def get_heading_from_degrees(degrees):
        '''
        Provided a heading in degrees return an enumerated cardinal direction.
        '''
        _value = round((degrees / 45.0) + 0.5)
        _array = [ Cardinal.NORTH, Cardinal.NORTHEAST, Cardinal.EAST, Cardinal.SOUTHEAST, Cardinal.SOUTH, Cardinal.SOUTHWEST, Cardinal.WEST, Cardinal.NORTHWEST ]
        return _array[(_value % 8)];

    @staticmethod
    def get_heading_from_degrees_old(degrees):
        '''
        Provided a heading in degrees return an enumerated cardinal direction.
        '''
        if 0 <= degrees <= 67.5:
            return Cardinal.NORTHEAST
        elif 67.5  <= degrees <= 112.5:
            return Cardinal.EAST
        elif degrees > 337.25 or degrees < 22.5:
            return Cardinal.NORTH
        elif 292.5 <= degrees <= 337.25:
            return Cardinal.NORTHWEST
        elif 247.5 <= degrees <= 292.5:
            return Cardinal.WEST
        elif 202.5 <= degrees <= 247.5:
            return Cardinal.SOUTHWEST
        elif 157.5 <= degrees <= 202.5:
            return Cardinal.SOUTH
        elif 112.5 <= degrees <= 157.5:
            return Cardinal.SOUTHEAST


# ..............................................................................
class ActionState(Enum):
    INIT             = 1
    STARTED          = 2
    COMPLETED        = 3
    CLOSED           = 4

