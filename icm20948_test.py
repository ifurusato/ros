#!/usr/bin/env python3

import sys, time, traceback
from icm20948 import ICM20948
from colorama import init, Fore, Style
init()

from lib.logger import Level, Logger
from lib.config_loader import ConfigLoader

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
        self._log.info('ready.')

    def read_magnetometer(self):
        return self._icm20948.read_magnetometer_data()

    def read_accelerometer_gyro(self):
        return self._icm20948.read_accelerometer_gyro_data()

# main .........................................................................
def main(argv):

    try:

        # read YAML configuration
        _loader = ConfigLoader(Level.INFO)
        filename = 'config.yaml'
        _config = _loader.configure(filename)

        _imu = IMU(_config, Level.INFO)

        while True:
            x, y, z = _imu.read_magnetometer()
            ax, ay, az, gx, gy, gz = _imu.read_accelerometer_gyro()
            print(Fore.CYAN    + 'Accel: {:05.2f} {:05.2f} {:05.2f} '.format(ax, ay, az) \
                + Fore.YELLOW  + '\tGyro: {:05.2f} {:05.2f} {:05.2f} '.format(gx, gy, gz )\
                + Fore.MAGENTA + '\tMag: {:05.2f} {:05.2f} {:05.2f}'.format(x, y, z) + Style.RESET_ALL)
            time.sleep(0.25)

    except KeyboardInterrupt:
        print(Fore.CYAN + Style.BRIGHT + 'caught Ctrl-C; exiting...')
        
    except Exception:
        print(Fore.RED + Style.BRIGHT + 'error starting imu: {}'.format(traceback.format_exc()) + Style.RESET_ALL)

# call main ....................................................................
if __name__== "__main__":
    main(sys.argv[1:])

