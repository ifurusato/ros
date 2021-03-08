#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# Copyright 2020-2021 by Murray Altheim. All rights reserved. This file is part
# of the Robot Operating System project, released under the MIT License. Please
# see the LICENSE file included as part of this package.
#
# author:   Murray Altheim
# created:  2021-03-06
# modified: 2021-03-09
#

import itertools
from pa1010d import PA1010D, PPS
from colorama import init, Fore, Style
init()

from lib.logger import Level, Logger

class GPS(object):
    '''
    A wrapper around the PA1010d GPS library. Provides individual
    properties for each of the GPS outputs.
    '''
    def __init__(self, level):
        self._log = Logger("gps", level)
        self._counter = itertools.count()
        self._gps = PA1010D()
#       self._gps.set_pps(mode=PPS.ALWAYS)
        self._gps.set_pps(mode=PPS.ONLY_2D_3D)
        self.clear()
        self._log.info('ready.')

    # ..........................................................................
    def clear(self):
        self._timestamp, self._latitude, self._longitude, self._altitude, \
        self._sat_count, self._quality, self._speed, self._mf_type, \
        self._pdop, self._vdop, self._hdop = (None,)*11

    # ..........................................................................
    def read(self):
        self._count = next(self._counter)
        result = self._gps.update()
        if result:
            _data = self._gps.data
            if _data.get('timestamp') == None:
                self.clear()
            else:
                self._timestamp = _data.get('timestamp')
                self._latitude  = _data.get('latitude')
                self._longitude = _data.get('longitude')
                self._altitude  = _data.get('altitude')
                self._sat_count = _data.get('num_sats')
                self._quality   = _data.get('gps_qual')
                self._speed     = _data.get('speed_over_ground')
                self._mf_type   = _data.get('mode_fix_type')
                self._pdop      = _data.get('pdop')
                self._vdop      = _data.get('vdop')
                self._hdop      = _data.get('hdop')
        else:
            return None

    # ..........................................................................
    def display(self):
        if self._timestamp == None:
            self._log.info(Fore.CYAN + '  [{:06d}]'.format(self._count) + Fore.YELLOW + ' GPS returned null: no satellites found.')
        else:
            try:
                _color = Fore.BLUE if self._sat_count == 0 else Fore.YELLOW
                self._log.info(Fore.CYAN + '  [{:06d}]'.format(self._count) + _color \
                        + Fore.GREEN + ' time: {}; {} sat; q{};'.format(self._timestamp, self._sat_count, self._quality) \
                        + Fore.WHITE + ' lati-long: {:6.4f}, {:6.4f}; alt: {:5.2f}m; speed: {}m/s;'.format(self._latitude, self._longitude, self._altitude, self._speed) )
#                       + Fore.BLACK + ' fix type: {} PDOP: {} VDOP: {} HDOP: {}'.format(self._mf_type, self._pdop, self._vdop, self._hdop) )
            except Exception:
                pass


    # ..........................................................................
    @property
    def timestamp(self):
        return self._timestamp

    # ..........................................................................
    @property
    def latitude(self):
        return self._latitude

    # ..........................................................................
    @property
    def longitude(self):
        return self._longitude

    # ..........................................................................
    @property
    def altitude(self):
        return self._altitude

    # ..........................................................................
    @property
    def satellites(self):
        return self._sat_count

    # ..........................................................................
    @property
    def quality(self):
        return self._quality

    # ..........................................................................
    @property
    def speed(self):
        return self._speed

    # ..........................................................................
    @property
    def mode_fix_type(self):
        return self._mf_type

    # ..........................................................................
    @property
    def pdop(self):
        return self._pdop

    # ..........................................................................
    @property
    def vdop(self):
        return self._vdop

    # ..........................................................................
    @property
    def hdop(self):
        return self._hdop

#EOF
