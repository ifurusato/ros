#!/usr/bin/env python3

import sys, time, traceback, math
from icm20948 import ICM20948
from colorama import init, Fore, Style
init()

from lib.logger import Level, Logger
from lib.config_loader import ConfigLoader
from lib.convert import Convert

#X = 0
#Y = 1
#Z = 2
#AXES = Y, Z

# ..............................................................................
class IMU():
    '''
        An ICM20948-based Inertial Measurement Unit (IMU).
    '''
    def __init__(self, config, level):
        super().__init__()
        self._log = Logger('imu', level)
        if config is None:
            raise ValueError('no configuration provided.')
        _config = config['ros'].get('imu')
        self._icm20948 = ICM20948(i2c_addr=0x69)
        self._amin = list(self._icm20948.read_magnetometer_data())
        self._amax = list(self._icm20948.read_magnetometer_data())
        self._log.info('amin: {}; amax: {}'.format(type(self._amin), type(self._amax)))
        self._log.info('ready.')

    def read_magnetometer(self):
        return self._icm20948.read_magnetometer_data()

    def read_accelerometer_gyro(self):
        return self._icm20948.read_accelerometer_gyro_data()

#    def heading_from_magnetometer(self, mag):
#        mag = list(mag)
#        for i in range(3):
#            v = mag[i]
#            if v < self._amin[i]:
#                self._amin[i] = v
#            if v > self._amax[i]:
#                self._amax[i] = v
#            mag[i] -= self._amin[i]
#            try:
#                mag[i] /= self._amax[i] - self._amin[i]
#            except ZeroDivisionError:
#                pass
#            mag[i] -= 0.5
#    
#        heading = math.atan2(mag[AXES[0]], mag[AXES[1]])
#        if heading < 0:
#            heading += 2 * math.pi
#        heading = math.degrees(heading)
#        heading = int(round(heading))
#        return heading


# main .........................................................................
def main(argv):

    try:

        # read YAML configuration
        _loader = ConfigLoader(Level.INFO)
        filename = 'config.yaml'
        _config = _loader.configure(filename)

        _imu = IMU(_config, Level.INFO)

        while True:
#           x, y, z = _imu.read_magnetometer()
            mag = _imu.read_magnetometer()
#           ax, ay, az, gx, gy, gz = _imu.read_accelerometer_gyro()
            acc = _imu.read_accelerometer_gyro()
            heading = Convert.heading_from_magnetometer(_imu._amin, _imu._amax, mag)
            print(Fore.CYAN    + 'Accel: {:05.2f} {:05.2f} {:05.2f} '.format(acc[0], acc[1], acc[2]) \
                + Fore.YELLOW  + '\tGyro: {:05.2f} {:05.2f} {:05.2f} '.format(acc[3], acc[4], acc[5]) \
                + Fore.MAGENTA + '\tMag: {:05.2f} {:05.2f} {:05.2f}  '.format(mag[0], mag[1], mag[2]) \
                + Fore.GREEN   + '\tHeading: {:d}°'.format(heading) + Style.RESET_ALL)
            time.sleep(0.25)

    except KeyboardInterrupt:
        print(Fore.CYAN + Style.BRIGHT + 'caught Ctrl-C; exiting...')
        
    except Exception:
        print(Fore.RED + Style.BRIGHT + 'error starting imu: {}'.format(traceback.format_exc()) + Style.RESET_ALL)

# call main ....................................................................
if __name__== "__main__":
    main(sys.argv[1:])

