#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#### - - coding: latin-1 -*-

# import dependency libraries ..................................................

import sys, traceback
from fractions import Fraction
from colorama import init, Fore, Style
init()

pi = None

try:
    import pigpio
    pi = pigpio.pi()
    print('import            :' + Fore.CYAN + ' INFO  : successfully imported pigpio.' + Style.RESET_ALL)
except Exception:
#except ModuleNotFoundError:
    print('import            :' + Fore.RED + ' ERROR : failed to import pigpio, operating without Pi.' + Style.RESET_ALL)

try:
    import numpy
except ImportError:
    sys.exit("This script requires the numpy module.\nInstall with: sudo pip3 install numpy")

from lib.i2c_scanner import I2CScanner
from lib.enums import Orientation
from lib.logger import Logger, Level

# ..............................................................................
class Configurer():
    '''
        Scans the I2C bus and imports and configures the features corresponding 
        to the devices found. This includes importing the necessary libraries
        and adding the device to the ROS.

        This is designed to permit alternate hardware configurations, based on
        which I2C devices are on the bus.
    '''
    def __init__(self, ros, level):
        self._log = Logger("import", level)
        if ros is None:
            raise ValueError('null ros argument.')
        self._ros = ros
        try:
            scanner = I2CScanner(Level.WARN)
            self._addresses = scanner.getAddresses()
            hexAddresses = scanner.getHexAddresses()
            self._addrDict = dict(list(map(lambda x, y:(x,y), self._addresses, hexAddresses)))
            for i in range(len(self._addresses)):
                self._log.debug(Fore.BLACK + Style.DIM + 'found device at address: {}'.format(hexAddresses[i]) + Style.RESET_ALL)
        except Exception:
            self._log.info(traceback.format_exc())
            sys.exit(1)


    # ..........................................................................
    def _set_feature_available(self, name, value):
        '''
            A convenience method that sets a feature's availability
            to the boolean value.
        '''
        self._log.debug(Fore.BLUE + Style.BRIGHT + '-- set feature available. name: \'{}\' value: \'{}\'.'.format(name, value))
        self._ros.set_property('features', name, value)


    # ..........................................................................
    def scan(self):
        '''
            Scan all known addresses, configuring devices for those that exist
            on the bus.

            This also sets configuration properties so they're available elsewhere.
        '''

        # ............................................
        ht0740_available = ( 0x38 in self._addresses )
        if ht0740_available:
            self._log.debug(Fore.CYAN + Style.BRIGHT + '-- HT0740 Switch available at 0x38.' + Style.RESET_ALL)
            self._addresses.remove(0x38)
            self.configure_ht0740()
        else:
            self._log.debug(Fore.RED + Style.BRIGHT + '-- no HT0740 Switch available at 0x38.' + Style.RESET_ALL)
        self._set_feature_available('ht0740', ht0740_available)
    
        # ............................................
        self._configure_default_features()

        # ............................................
        thunderborg_available = ( 0x15 in self._addresses )
        if thunderborg_available:
            self._log.debug(Fore.CYAN + Style.BRIGHT + '-- ThunderBorg available at 0x15' + Style.RESET_ALL)
            self._addresses.remove(0x15)
            self._configure_thunderborg_motors()
        else:
            self._log.debug(Fore.RED + Style.BRIGHT + '-- no ThunderBorg available at 0x15.' + Style.RESET_ALL)
        self._set_feature_available('thunderborg', thunderborg_available)
    
        # ............................................
        ads1015_available = ( 0x48 in self._addresses )
        if ads1015_available:
            self._log.debug(Fore.CYAN + Style.BRIGHT + '-- ADS1015 AD Converter available at 0x48.' + Style.RESET_ALL)
            self._addresses.remove(0x48)
            self.configure_battery_check()
        else:
            self._log.debug(Fore.RED + Style.BRIGHT + '-- no ADS1015 AD Converter available at 0x48.' + Style.RESET_ALL)
        self._set_feature_available('ads1015', ads1015_available)
    
        # ............................................
        # the 5x5 RGB Matrix is at 0x74 for port, 0x77 for starboard
        rgbmatrix5x5_stbd_available = ( 0x74 in self._addresses )
        if rgbmatrix5x5_stbd_available:
            self._log.debug(Fore.CYAN + Style.BRIGHT + '-- RGB Matrix available at 0x74.' + Style.RESET_ALL)
            self._addresses.remove(0x74)
        else:
            self._log.debug(Fore.RED + Style.BRIGHT + '-- no RGB Matrix available at 0x74.' + Style.RESET_ALL)
        self._set_feature_available('rgbmatrix5x5_stbd', rgbmatrix5x5_stbd_available)

        rgbmatrix5x5_port_available = ( 0x77 in self._addresses )
        if rgbmatrix5x5_port_available:
            self._log.debug(Fore.CYAN + Style.BRIGHT + '-- RGB Matrix available at 0x77.' + Style.RESET_ALL)
            self._addresses.remove(0x77)
        else:
            self._log.debug(Fore.RED + Style.BRIGHT + '-- no RGB Matrix available at 0x77.' + Style.RESET_ALL)
        self._set_feature_available('rgbmatrix5x5_port', rgbmatrix5x5_port_available)

        if rgbmatrix5x5_stbd_available or rgbmatrix5x5_port_available:
            self.configure_rgbmatrix()
    
        # ............................................
        # the 11x7 LED matrix is at 0x75 for starboard, 0x77 for port. The latter
        # conflicts with the RGB LED matrix, so both cannot be used simultaneously.
        matrix11x7_stbd_available = ( 0x75 in self._addresses )
        if matrix11x7_stbd_available:
            self._log.debug(Fore.CYAN + Style.BRIGHT + '-- 11x7 Matrix LEDs available at 0x75.' + Style.RESET_ALL)
            self._addresses.remove(0x75)
            from lib.matrix import Matrix
        else:
            self._log.debug(Fore.RED + Style.BRIGHT + '-- no 11x7 Matrix LEDs available at 0x75.' + Style.RESET_ALL)
        self._set_feature_available('matrix11x7_stbd', matrix11x7_stbd_available)


        # ............................................
        bno055_available = ( 0x28 in self._addresses )
        if bno055_available:
            self._log.debug(Fore.CYAN + Style.BRIGHT + '-- BNO055 orientation sensor available at 0x28.' + Style.RESET_ALL)
            self._addresses.remove(0x28)
            self.configure_bno055()
        else:
            self._log.debug(Fore.RED + Style.BRIGHT + '-- no BNO055 orientation sensor available at 0x28.' + Style.RESET_ALL)
        self._set_feature_available('bno055', bno055_available)
    
        # ............................................
        lsm303d_available = ( 0x1D in self._addresses )
        if lsm303d_available:
            self._log.debug(Fore.CYAN + Style.BRIGHT + '-- LSM303D available at 0x1D.' + Style.RESET_ALL)
            self._addresses.remove(0x1D)
    #       from lib.matrix import Matrix
        else:
            self._log.debug(Fore.RED + Style.BRIGHT + '-- no LSM303D available at 0x1D.' + Style.RESET_ALL)
        self._set_feature_available('lsm303d', lsm303d_available)
    
        # ............................................
        vl53l1x_available = ( 0x29 in self._addresses )
        if vl53l1x_available:
            self._log.debug(Fore.CYAN + Style.BRIGHT + '-- VL53L1X available at 0x29.' + Style.RESET_ALL)
            self._addresses.remove(0x29)
    #       from lib.matrix import Matrix
        else:
            self._log.debug(Fore.RED + Style.BRIGHT + '-- no VL53L1X available at 0x29.' + Style.RESET_ALL)
        self._set_feature_available('vl53l1x', vl53l1x_available)
    
        # ............................................
        ultraborg_available = ( 0x36 in self._addresses )
        if ultraborg_available:
            self._log.debug(Fore.CYAN + Style.BRIGHT + '-- UltraBorg available at 0x36.' + Style.RESET_ALL)
            self._addresses.remove(0x36)
    #       from lib.matrix import Matrix
        else:
            self._log.debug(Fore.RED + Style.BRIGHT + '-- no UltraBorg available at 0x36.' + Style.RESET_ALL)
        self._set_feature_available('ultraborg', ultraborg_available)
    
        # ............................................
        as7262_available = ( 0x49 in self._addresses )
        if as7262_available:
            self._log.debug(Fore.CYAN + Style.BRIGHT + '-- AS7262 Spectrometer available at 0x49.' + Style.RESET_ALL)
            self._addresses.remove(0x49)
    #       from lib.matrix import Matrix
        else:
            self._log.debug(Fore.RED + Style.BRIGHT + '-- no AS7262 Spectrometer available at 0x49.' + Style.RESET_ALL)
        self._set_feature_available('as7262', as7262_available)
    
        # ............................................
        pijuice_available = ( 0x68 in self._addresses )
        if pijuice_available:
            self._log.debug(Fore.CYAN + Style.BRIGHT + '-- PiJuice hat available at 0x68.' + Style.RESET_ALL)
            self._addresses.remove(0x68)
    #       from lib.matrix import Matrix
        else:
            self._log.debug(Fore.RED + Style.BRIGHT + '-- no PiJuice hat available at 0x68.' + Style.RESET_ALL)
        self._set_feature_available('pijuice', pijuice_available)
    
        # ............................................
        # NOTE: the default address for the ICM20948 is 0x68, but this conflicts with the PiJuice
        icm20948_available = ( 0x69 in self._addresses )
        if icm20948_available:
            self._log.debug(Fore.CYAN + Style.BRIGHT + '-- ICM20948 available at 0x69.' + Style.RESET_ALL)
            self._addresses.remove(0x69)
    #       from lib.matrix import Matrix
        else:
            self._log.debug(Fore.RED + Style.BRIGHT + '-- no ICM20948 available at 0x69.' + Style.RESET_ALL)
        self._set_feature_available('icm20948', icm20948_available)
    

    # ..........................................................................
    def _configure_default_features(self):
        '''
            Import dependencies and configure default features.
        '''
        self._log.warning('configure default features...')
        from lib.button import Button
        self._log.info('configuring button...')
        self._ros._button = Button(self._ros._config, self._ros.get_message_queue(), self._ros._mutex)

#       from lib.bumpers import Bumpers
#       self._log.info('configuring bumpers...')
#       self._ros._bumpers = Bumpers(self._ros._config, self._ros.get_message_queue(), None, Level.INFO)

#       from lib.infrareds import Infrareds
#       self._ros._infrareds = Infrareds(self._ros._config, self._ros.get_message_queue(), Level.INFO)

        self._log.info('configuring integrated front sensors...')
        from lib.ifs import IntegratedFrontSensor
        self._ros._ifs = IntegratedFrontSensor(self._ros._config, self._ros._queue, Level.INFO)

#       from lib.player import Sound, Player
#       self._log.info('configuring player...')
#       self._ros._player = Player(Level.INFO)

        self._log.warning('default features ready.')


    # ..........................................................................
    def _configure_thunderborg_motors(self):
        '''
            Import the ThunderBorg library, then configure the Motors.
        '''
        self._log.warning('configure thunderborg & motors...')
        global pi
        try:
            self._log.info('importing ThunderBorg...')
#           sys.path.append('/home/pi/thunderborg')
            import lib.ThunderBorg3 as ThunderBorg
            self._log.info('successfully imported ThunderBorg.')
            TB = ThunderBorg.ThunderBorg()  # create a new ThunderBorg object
            TB.Init()                       # set the board up (checks the board is connected)
            self._log.info('successfully instantiated ThunderBorg.')

            if not TB.foundChip:
                boards = ThunderBorg.ScanForThunderBorg()
                if len(boards) == 0:
                    self._log.error('No ThunderBorg found, check you are attached :)')
                else:
                    self._log.error('No ThunderBorg at address %02X, but we did find boards:' % (TB.i2cAddress))
                    for board in boards:
                        self._log.info('    %02X (%d)' % (board, board))
                    self._log.error('If you need to change the I²C address change the setup line so it is correct, e.g. TB.i2cAddress = 0x{}'.format(boards[0]))
                sys.exit(1)
            TB.SetLedShowBattery(True)
    
            # initialise ThunderBorg ...........................
            self._log.debug('getting battery reading...')
            # get battery voltage to determine max motor power
            # could be: Makita 12V or 18V power tool battery, or 12V line supply
            voltage_in = TB.GetBatteryReading()
            if voltage_in is None:
                raise OSError('cannot continue: cannot read battery voltage.')
            self._log.info('voltage in: {:>5.2f}V'.format(voltage_in))
    #       voltage_in = 20.5
            # maximum motor voltage
            voltage_out = 9.0
            self._log.info('voltage out: {:>5.2f}V'.format(voltage_out))
            if voltage_in < voltage_out:
                raise OSError('cannot continue: battery voltage too low ({:>5.2f}V).'.format(voltage_in))
            # Setup the power limits
            if voltage_out > voltage_in:
                _max_power_ratio = 1.0
            else:
                _max_power_ratio = voltage_out / float(voltage_in)
            # convert float to ratio format
            self._log.info('battery level: {:>5.2f}V; motor voltage: {:>5.2f}V; maximum power ratio: {}'.format(voltage_in, voltage_out, \
                    str(Fraction(_max_power_ratio).limit_denominator(max_denominator=20)).replace('/',':')))

        except Exception as e:
            self._log.error('unable to import ThunderBorg: {}'.format(e))
            traceback.print_exc(file=sys.stdout)
            sys.exit(1)

        # now import motors
        from lib.motors import Motors
        try:
            self._log.info('configuring motors...')
            self._ros._motors = Motors(self._ros._config, TB, pi, Level.INFO)
            self._ros._motors.get_motor(Orientation.PORT).set_max_power_ratio(_max_power_ratio)
            self._ros._motors.get_motor(Orientation.STBD).set_max_power_ratio(_max_power_ratio)
        except OSError as oe:
            self._log.error('failed to configure motors: {}'.format(oe))
#           sys.stderr = DevNull()
            sys.exit(1)


    # ..........................................................................
    def configure_ht0740(self):
        self._log.warning('configure ht0740...')
        from lib.switch import Switch
        self._log.info('configuring switch...')
        self._ros._switch = Switch(Level.INFO)
        # since we're using the HT0740 Switch we need to turn it on to enable
        # the sensors that rely upon its power 
#       self._ros._switch.enable()
        self._ros._switch.on()
        
#       _switch = Switch(Level.INFO)
#       self._ros.add_feature(_switch)


    # ..........................................................................
    def configure_battery_check(self):
        self._log.warning('configure battery check...')
        from lib.batterycheck import BatteryCheck
        _battery_check = BatteryCheck(self._ros._config, self._ros.get_message_queue(), Level.INFO)
        self._ros.add_feature(_battery_check)


    # ..........................................................................
    def configure_rgbmatrix(self):
        self._log.warning('configure rgbmatrix...')
        from lib.rgbmatrix import RgbMatrix, DisplayType
        self._log.debug('configuring random blinky display...')
#       self._ros._rgbmatrix = RgbMatrix(Level.INFO)
        self._ros._rgbmatrix = RgbMatrix(Level.INFO)
        self._ros.add_feature(self._ros._rgbmatrix) # FIXME this is added twice


    # ..........................................................................
    def configure_bno055(self):
        self._log.warning('configure bno055...')
        from lib.bno055 import BNO055
        self._log.info('configuring BNO055 9DoF sensor...')
        self._ros._bno055 = BNO055(self._ros.get_message_queue(), Level.INFO)



    # ..........................................................................
    def summation():
        self._log.info(Fore.YELLOW + '-- unaccounted for self._addresses:')
        for i in range(len(self._addresses)):
            hexAddr = self._addrDict.get(self._addresses[i])
            self._log.info(Fore.YELLOW + Style.BRIGHT + '-- address: {}'.format(hexAddr) + Style.RESET_ALL)

            
#EOF
