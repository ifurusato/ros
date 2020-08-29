#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# Copyright 2020 by Murray Altheim. All rights reserved. This file is part of
# the Robot Operating System project and is released under the "Apache Licence,
# Version 2.0". Please see the LICENSE file included as part of this package.
#
# author:   Murray Altheim
# created:  2020-08-20
# modified: 2020-08-20
#
#  Creates a class wrapping the accelerometer of the LSM303D, with the main()
#  method testing its functionality.
#

import sys, time, math
from lsm303d import LSM303D
from colorama import init, Fore, Style
init()

from lib.config_loader import ConfigLoader
from lib.logger import Level, Logger

class Accelerometer():
    '''
        * roll is negative clockwise, positive counter-clockwise
        * yaw is not valid when at rest since gravity is the same for all orientations
        * pitch is negative if going downhill, positive if uphill

        Configuration: jitter limit is how much jitter is permitted from the sensor
        while still considered at rest.
    '''
    def __init__(self, config, level):
        super().__init__()
        if config is None:
            raise ValueError("no configuration provided.")
        _config = config['ros'].get('accelerometer')
        self._jitter_limit = _config.get('jitter_limit')

        self._lsm = LSM303D(0x1d)  # Change to 0x1e if you have soldered the address jumper
        self._log = Logger('accel', level)
        self._x_offset = None
        self._y_offset = None
        self._z_offset = None
        self.calibrate()
        self._log.info('ready.')

    # ..........................................................................
    def calibrate(self):
        calibration_xyz = self._lsm.accelerometer()
        self._x_offset = calibration_xyz[0]
        self._y_offset = calibration_xyz[1]
        self._z_offset = calibration_xyz[2]
        self._log.info( 'calibration: ' \
             + Fore.RED   + 'roll offset: {:+06.2f}g : '.format(self._x_offset) \
             + Fore.GREEN + 'yaw offset: {:+06.2f}g : '.format(self._y_offset) \
             + Fore.BLUE  + 'pitch offset: {:+06.2f}g'.format(self._z_offset) + Style.RESET_ALL)

    # ..........................................................................
    def at_rest(self, ):
        _xyz = self._lsm.accelerometer()
        return not ( self.is_moving(_xyz[0] - self._x_offset) \
            or self.is_moving(_xyz[1] - self._y_offset) \
            or self.is_moving(_xyz[2] - self._z_offset) )

    # ..........................................................................
    def get_roll(self):
        return self._lsm.accelerometer()[0]

    # ..........................................................................
    def get_yaw(self):
        return self._lsm.accelerometer()[1]

    # ..........................................................................
    def get_pitch(self):
        return self._lsm.accelerometer()[2]

    # ..........................................................................
    def get_xyz(self):
        '''
            Returns an accelerometer measurement as an [x,y,z] tuple, i.e., roll,
            yaw, pitch, assuming the sensor is installed upwards, facing forward
            on the robot. This is more efficient if you want more than one axis
            for the same moment, where roll = v[0], yaw = v[1] and pitch = v[2].
        '''
        return self._lsm.accelerometer()

    # ..........................................................................
    def is_moving(self, x):
        return not (min((-1.0 * self._jitter_limit) , self._jitter_limit) < x < max((-1.0 * self._jitter_limit), self._jitter_limit) )


# call main ....................................................................
def main():

    # read YAML configuration
    _loader = ConfigLoader(Level.INFO)
    filename = 'config.yaml'
    _config = _loader.configure(filename)
        
    _accel = Accelerometer(_config, Level.INFO)

    try:
        while True:

            _xyz = _accel.get_xyz()
            _x = _xyz[0] - _accel._x_offset
            _y = _xyz[1] - _accel._y_offset
            _z = _xyz[2] - _accel._z_offset

            _roll_style  = Fore.CYAN + Style.BRIGHT    if _accel.is_moving(_x) else Fore.RED + Style.NORMAL
            _yaw_style   = Fore.MAGENTA + Style.BRIGHT if _accel.is_moving(_y) else Fore.GREEN + Style.NORMAL
            _pitch_style = Fore.YELLOW + Style.BRIGHT  if _accel.is_moving(_z) else Fore.BLUE + Style.NORMAL
            _at_rest = _accel.at_rest()

            print( _roll_style + 'roll: {:+06.2f}g '.format(_x) \
                 + _yaw_style + '\tyaw: {:+06.2f}g '.format(_y) \
                 + _pitch_style + '\tpitch: {:+06.2f}g '.format(_z) + Fore.WHITE + Style.NORMAL \
                 + '\tat rest? {}'.format(_at_rest) + Style.RESET_ALL)

            time.sleep(1.0/50)

    except KeyboardInterrupt:
        print(Fore.RED + 'caught Ctrl-C; exiting...' + Style.RESET_ALL)

if __name__== "__main__":
    main()

