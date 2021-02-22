#!/usr/bin/env python3
#
# Copyright 2020 by Murray Altheim. All rights reserved. This file is part of
# the Robot OS project and is released under the "Apache Licence, Version 2.0".
# Please see the LICENSE file included as part of this package.
#
# author:   Murray Altheim
# created:  2020-02-21
# modified: 2020-03-26
#

from enum import Enum

class Event(Enum):
    '''
    Ballistic behaviours cannot be interrupted, and are not therefore
    implemented as a separate thread.

    The specific response for a behaviour is provided by the Controller,
    which receives an Event-laden Message from the Arbitrator, which
    prioritises the Messages it receives from the MessageQueue.

    For non-ballistic behaviours the response is generally an ongoing
    setting a pair of motor speeds.

    For ballistic behaviours the Controller's script for a given
    behaviour is meant to be uninterruptable. The goal here is to
    permit interruptions from *higher* priority events.
    '''
    # name                     n   description             priority  ballistic?
    # system events ....................
    NOOP                   = ( 0, "no operation",             0,     False)
    BATTERY_LOW            = ( 1, "battery low",              0,     True)
    SHUTDOWN               = ( 2, "shutdown",                 1,     True)
    HIGH_TEMPERATURE       = ( 3, "high temperature",         1,     False)
    # stopping and halting .............
    STOP                   = ( 4, "stop",                     2,     True)
    HALT                   = ( 5, "halt",                     3,     False)
    BRAKE                  = ( 6, "brake",                    4,     False)
    BUTTON                 = ( 7, "button",                   5,     False)
    STANDBY                = ( 8, "standby",                  6,     False)
    # bumper ...........................
    BUMPER_PORT            = ( 10, "bumper port",             10,    True)
    BUMPER_CNTR            = ( 11, "bumper center",           10,    True)
    BUMPER_STBD            = ( 12, "bumper starboard",        10,    True)
    # infrared .........................
    INFRARED_PORT_SIDE     = ( 20, "infrared port side",      20,    True)
    INFRARED_PORT          = ( 21, "infrared port",           20,    True)
    INFRARED_CNTR          = ( 22, "infrared cntr",           20,    True)
    INFRARED_STBD          = ( 23, "infrared stbd",           20,    True)
    INFRARED_STBD_SIDE     = ( 24, "infrared stbd side",      20,    True)

    # emergency movements ..............
    EMERGENCY_ASTERN       = ( 30, "emergency astern",        15,    True)
    # movement ahead ...................
    FULL_AHEAD             = ( 45, "full ahead",              100,   False)
    HALF_AHEAD             = ( 46, "half ahead",              100,   False)
    SLOW_AHEAD             = ( 47, "slow ahead",              100,   False)
    DEAD_SLOW_AHEAD        = ( 48, "dead slow ahead",         100,   False)
    AHEAD                  = ( 49, "ahead",                   100,   False)
    # movement astern ..................
    ASTERN                 = ( 50, "astern",                  100,   False)
    DEAD_SLOW_ASTERN       = ( 51, "dead slow astern",        100,   False)
    SLOW_ASTERN            = ( 52, "slow astern",             100,   False)
    HALF_ASTERN            = ( 53, "half astern",             100,   False)
    FULL_ASTERN            = ( 54, "full astern",             100,   False)
    # relative change ..................
    INCREASE_SPEED         = ( 60, "increase speed",          100,   False)
    EVEN                   = ( 61, "even",                    100,   False)
    DECREASE_SPEED         = ( 62, "decrease speed",          100,   False)
    # port turns .......................
    TURN_AHEAD_PORT        = ( 70, "turn ahead port",         100,   False)
    TURN_TO_PORT           = ( 71, "turn to port",            100,   False)
    TURN_ASTERN_PORT       = ( 72, "turn astern port",        100,   False)
    SPIN_PORT              = ( 73, "spin port",               100,   False)
    # starboard turns ..................
    SPIN_STBD              = ( 80, "spin starboard",          100,   False)
    TURN_ASTERN_STBD       = ( 81, "turn astern starboard",   100,   False)
    TURN_TO_STBD           = ( 82, "turn to starboard",       100,   False)
    TURN_AHEAD_STBD        = ( 83, "turn ahead starboard",    100,   False)
    # high level behaviours ............
    ROAM                   = ( 90, "roam",                    100,   False)
    SNIFF                  = ( 91, "A: sniff",                100,    True) # A Button
    VIDEO                  = ( 92, "L1: video",               150,   False) # L1 Button
    EVENT_L2               = ( 93, "L2",                      150,   False) # L2 Button
    EVENT_R1               = ( 94, "R1: cruise",              150,   False) # R1 Button
    LIGHTS                 = ( 95, "R2: lights",              150,   False) # R2 Button

    # movement directives ..............
    FORWARD_VELOCITY       = ( 101, "forward velocity",       200,   False)
    THETA                  = ( 102, "theta",                  200,   False)
    PORT_VELOCITY          = ( 103, "port velocity",          200,   False)
    PORT_THETA             = ( 104, "port theta",             200,   False)
    STBD_VELOCITY          = ( 105, "starboard velocity",     200,   False)
    STBD_THETA             = ( 106, "starboard theta",        200,   False)

    # other behaviours (> 500) .........
    NO_ACTION              = ( 500, "no action",              500,   False)
    CLOCK_TICK             = ( 501, "tick",                   500,   False)
    CLOCK_TOCK             = ( 502, "tock",                   500,   False)

    @property
    def is_ignoreable(self):
        '''
        Returns true if the priority of this event is 500 or greater.
        By definition this includes NO_ACTION, CLOCK_TICK and CLOCK_TOCK.
        '''
        return self._priority >= 500

    # ..................................
    def __new__(cls, *args, **kwds):
        obj = object.__new__(cls)
        obj._value_ = args[0]
        return obj

    # ignore the first param since it's already set by __new__
    def __init__(self, num, description, priority, is_ballistic):
        self._description = description
        self._priority = priority
        self._is_ballistic = is_ballistic

    # this makes sure the description is read-only
    @property
    def description(self):
        return self._description

    # this makes sure the priority property is read-only
    @property
    def priority(self):
        return self._priority

    # this makes sure the ballistic property is read-only
    @property
    def is_ballistic(self):
        return self._is_ballistic

    # the normal value returned for an enum
    def __str__(self):
        return self.name

    @staticmethod
    def from_str(label):
        # system events ....................
        if label.upper() == 'BATTERY_LOW': 
            return Event.BATTERY_LOW
        elif label.upper() == 'SHUTDOWN': 
            return Event.SHUTDOWN
        # stopping and halting .............
        elif label.upper() == 'STOP': 
            return Event.STOP
        elif label.upper() == 'HALT': 
            return Event.HALT
        elif label.upper() == 'BRAKE': 
            return Event.BRAKE
        elif label.upper() == 'BUTTON': 
            return Event.BUTTON
        elif label.upper() == 'STANDBY': 
            return Event.STANDBY
        # bumper ...........................
        elif label.upper() == 'BUMPER_PORT': 
            return Event.BUMPER_PORT
        elif label.upper() == 'BUMPER_CNTR': 
            return Event.BUMPER_CNTR
        elif label.upper() == 'BUMPER_STBD': 
            return Event.BUMPER_STBD
        # infrared .........................
        elif label.upper() == 'INFRARED_PORT': 
            return Event.INFRARED_PORT
        elif label.upper() == 'INFRARED_CNTR': 
            return Event.INFRARED_CNTR
        elif label.upper() == 'INFRARED_STBD': 
            return Event.INFRARED_STBD
        elif label.upper() == 'INFRARED_PORT_SIDE': 
            return Event.INFRARED_PORT_SIDE
        elif label.upper() == 'INFRARED_STBD_SIDE': 
            return Event.INFRARED_STBD_SIDE
        # emergency movements ..............
        elif label.upper() == 'EMERGENCY_ASTERN': 
            return Event.EMERGENCY_ASTERN
        # movement ahead ...................
        elif label.upper() == 'FULL_AHEAD': 
            return Event.FULL_AHEAD
        elif label.upper() == 'HALF_AHEAD': 
            return Event.HALF_AHEAD
        elif label.upper() == 'SLOW_AHEAD': 
            return Event.SLOW_AHEAD
        elif label.upper() == 'DEAD_SLOW_AHEAD': 
            return Event.DEAD_SLOW_AHEAD
        elif label.upper() == 'AHEAD': 
            return Event.AHEAD
        # movement astern ..................
        elif label.upper() == 'ASTERN': 
            return Event.ASTERN
        elif label.upper() == 'DEAD_SLOW_ASTERN': 
            return Event.DEAD_SLOW_ASTERN
        elif label.upper() == 'SLOW_ASTERN': 
            return Event.SLOW_ASTERN
        elif label.upper() == 'HALF_ASTERN': 
            return Event.HALF_ASTERN
        elif label.upper() == 'FULL_ASTERN': 
            return Event.FULL_ASTERN
        # relative change ..................
        elif label.upper() == 'INCREASE_SPEED': 
            return Event.INCREASE_SPEED
        elif label.upper() == 'EVEN': 
            return Event.EVEN
        elif label.upper() == 'DECREASE_SPEED': 
            return Event.DECREASE_SPEED
        # port turns .......................
        elif label.upper() == 'TURN_AHEAD_PORT': 
            return Event.TURN_AHEAD_PORT
        elif label.upper() == 'TURN_TO_PORT': 
            return Event.TURN_TO_PORT
        elif label.upper() == 'TURN_ASTERN_PORT': 
            return Event.TURN_ASTERN_PORT
        elif label.upper() == 'SPIN_PORT': 
            return Event.SPIN_PORT
        # starboard turns ..................
        elif label.upper() == 'SPIN_STBD': 
            return Event.SPIN_STBD
        elif label.upper() == 'TURN_ASTERN_STBD': 
            return Event.TURN_ASTERN_STBD
        elif label.upper() == 'TURN_TO_STBD': 
            return Event.TURN_TO_STBD
        elif label.upper() == 'TURN_AHEAD_STBD': 
            return Event.TURN_AHEAD_STBD
        # high level behaviours ............
        elif label.upper() == 'ROAM': 
            return Event.ROAM
        elif label.upper() == 'FORWARD_VELOCITY':     
            return Event.FORWARD_VELOCITY
        elif label.upper() == 'THETA':               
            return Event.THETA
        elif label.upper() == 'PORT_VELOCITY':      
            return Event.PORT_VELOCITY
        elif label.upper() == 'PORT_THETA':        
            return Event.PORT_THETA
        elif label.upper() == 'STBD_VELOCITY':   
            return Event.STBD_VELOCITY
        elif label.upper() == 'STBD_THETA':      
            return Event.STBD_THETA
        elif label.upper() == 'SNIFF':      
            return Event.SNIFF

        elif label.upper() == 'NO_ACTION':      
            return Event.NO_ACTION
        else:
            raise NotImplementedError


#EOF
