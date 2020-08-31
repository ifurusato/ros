#!/usr/bin/env python3

#from __future__ import division, print_function
import sys, time
from colorama import init, Fore, Style
init()

from lib.config_loader import ConfigLoader
from lib.logger import Level, Logger
from lib.queue import MessageQueue
from lib.indicator import Indicator
from lib.nxp9dof import NXP9DoF

"""
accel/mag - 0x1f
gyro - 0x21
pi@r2d2 nxp $ sudo i2cdetect -y 1
    0  1  2  3  4  5  6  7  8  9  a  b  c  d  e  f
00:          -- -- -- -- -- -- -- -- -- -- -- -- --
10: -- -- -- -- -- -- -- -- -- -- -- -- -- -- -- 1f
20: -- 21 -- -- -- -- -- -- -- -- -- -- -- -- -- --
30: -- -- -- -- -- -- -- -- -- -- -- -- -- -- -- --
40: -- -- -- -- -- -- -- -- -- -- -- -- -- -- -- --
50: -- -- -- -- -- -- -- -- -- -- -- -- -- -- -- --
60: -- -- -- -- -- -- -- -- -- -- -- -- -- -- -- --
70: -- -- -- -- -- -- -- --
"""

class NXP():

    def __init__(self, imu):
        self._imu = imu
#       self._imu = IMU(gs=4, dps=2000, verbose=True)
#       imu = IMU(gs=4, dps=2000, verbose=True)

    # ..........................................................................
    def imu(self, count):
        header = 67
        print('-'*header)
        print("| {:17} | {:20} | {:20} |".format("Accels [g's]", " Magnet [uT]", "Gyros [dps]"))
        print('-'*header)
        for _ in range(count):
            a, m, g = self._imu.get()
            print('| {:>5.2f} {:>5.2f} {:>5.2f} | {:>6.1f} {:>6.1f} {:>6.1f} | {:>6.1f} {:>6.1f} {:>6.1f} |'.format(
                a[0], a[1], a[2],
                m[0], m[1], m[2],
                g[0], g[1], g[2])
            )
            time.sleep(0.50)
        print('-'*header)
        print(' uT: micro Tesla')
        print('  g: gravity')
        print('dps: degrees per second')
        print('')
    
    # ..........................................................................
    def ahrs(self, count):
        print('')
        header = 47
        print('-'*header)
        print("| {:20} | {:20} |".format("Accels [g's]", "Orient(r,p,h) [deg]"))
        print('-'*header)
        for _ in range(count):
            a, m, g = self._imu.get()
            r, p, h = self._imu.getOrientation(a, m)
            print(Fore.GREEN + '| {:>6.1f} {:>6.1f} {:>6.1f} | {:>6.1f} {:>6.1f} {:>6.1f} |'.format(a[0], a[1], a[2], r, p, h) + Style.RESET_ALL)
            time.sleep(0.50)
        print('-'*header)
        print('  r: roll')
        print('  p: pitch')
        print('  h: heading')
        print('  g: gravity')
        print('deg: degree')
        print('')
    
    # ..........................................................................
    def ahrs2(self, count):
        print('')
        header = 47
        print('-'*header)
        print(Fore.MAGENTA + "| {:20} | {:20} |".format("Accels [g's]", "Orient(r,p,h) [deg]") + Style.RESET_ALL)
        print(Fore.CYAN    + "| {:20} | {:20} |".format("Magnet [uT]", "Gyros [dps]") + Style.RESET_ALL)
        print('-'*header)
        for _ in range(count):
            a, m, g = self._imu.get()
            r, p, h = self._imu.getOrientation(a, m)
            print(Fore.MAGENTA + '| {:>6.1f} {:>6.1f} {:>6.1f} | {:>6.1f} {:>6.1f} {:>6.1f} |'.format(a[0], a[1], a[2], r, p, h) + Style.RESET_ALL)
            print(Fore.CYAN  + '| {:>6.1f} {:>6.1f} {:>6.1f} | {:>6.1f} {:>6.1f} {:>6.1f} |'.format(m[0], m[1], m[2], g[0], g[1], g[2]) + Style.RESET_ALL)
            time.sleep(0.50)
        print('-'*header)
        print('  r: roll')
        print('  p: pitch')
        print('  h: heading')
        print('  g: gravity')
        print('deg: degree')
        print('')
    
    # ..........................................................................
    def heading(self, count):
        print('')
        for _ in range(count):
            a, m, g = self._imu.get()
            _r, _p, _h = self._imu.getOrientation(a, m)
            
            _roll = _r * 100.0
            _pitch = _p * 100.0
            _heading = _h * 100.0
            print(Fore.MAGENTA + 'pitch: {:>6.4f}\troll: {:>6.4f}\theading: {:>6.4f}°'.format(_pitch, _roll, _heading) + Style.RESET_ALL)
            time.sleep(0.50)
    


# ..............................................................................
def main():

    try:

        # read YAML configuration
        _loader = ConfigLoader(Level.INFO)
        filename = 'config.yaml'
        _config = _loader.configure(filename)
        _queue = MessageQueue(Level.INFO)

        _nxp9dof = NXP9DoF(_config, _queue, Level.INFO)
        _nxp = NXP(_nxp9dof.get_imu())

        while True:
            print(Fore.CYAN + Style.BRIGHT + 'ahrs...' + Style.RESET_ALL)
            _nxp.heading(20)
#           _nxp.ahrs2(20)
#           _nxp.ahrs(10)
#           time.sleep(1.0)
#           print(Fore.CYAN + Style.BRIGHT + 'imu...' + Style.RESET_ALL)
#           _nxp.imu(10)
            time.sleep(1.0)

    except KeyboardInterrupt:
        print(Fore.RED + 'Ctrl-C caught; exiting...' + Style.RESET_ALL)

if __name__== "__main__":
    main()

#EOF
