#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# Copyright 2020-2021 by Murray Altheim. All rights reserved. This file is part
# of the Robot Operating System project, released under the MIT License. Please
# see the LICENSE file included as part of this package.
#
# author:   Murray Altheim
# created:  2019-12-23
# modified: 2020-03-12
#
# The NZPRG Robot Operating System (ROS), including its command line interface (CLI).
#
#        1         2         3         4         5         6         7         8         9         C
#234567890123456789012345678901234567890123456789012345678901234567890123456789012345678901234567890

# ..............................................................................
import os, sys, signal, time, threading, traceback
import argparse, psutil, itertools, yaml
from pathlib import Path
from colorama import init, Fore, Style
init()

#import RPi.GPIO as GPIO
#rom lib.import_gpio import *

from lib.logger import Level, Logger
from lib.rate import Rate
from lib.i2c_scanner import I2CScanner
from lib.devnull import DevNull
from lib.config_loader import ConfigLoader
from lib.event import Event
from lib.message import Message
from lib.abstract_task import AbstractTask 
from lib.message import Message
from lib.message_bus import MessageBus
from lib.message_factory import MessageFactory
from lib.clock import Clock
from lib.queue import MessageQueue
from lib.arbitrator import Arbitrator
from lib.controller import Controller

#from lib.indicator import Indicator
#from lib.gamepad import Gamepad, GamepadConnectException

# standard features:
from lib.motor_configurer import MotorConfigurer
from lib.motors import Motors
from lib.ifs import IntegratedFrontSensor
from lib.temperature import Temperature

#from lib.lidar import Lidar
#from lib.matrix import Matrix
#from lib.rgbmatrix import RgbMatrix, DisplayType
#from lib.bno055 import BNO055

led_0_path = '/sys/class/leds/led0/brightness'
led_1_path = '/sys/class/leds/led1/brightness'

# ==============================================================================

# ROS ..........................................................................
class ROS(AbstractTask):
    '''
    Extends AbstractTask as a Finite State Machine (FSM) basis of a Robot 
    Operating System (ROS) or behaviour-based system (BBS), including 
    spawning the various tasks and an Arbitrator as separate threads, 
    inter-communicating over a common message queue.

    This establishes the basic subsumption foundation of a MessageBus, a
    MessageFactory, a system Clock, an Arbitrator and a Controller.

    The MessageBus receives Event-containing messages from sensors and other
    message sources, which are passed on to the Arbitrator, whose job it is
    to determine the highest priority action to execute for that task cycle,
    by passing it on to the Controller.

    There is also a rosd linux daemon, which can be used to start, enable
    and disable ros. 

    :param mutex:   the optional logging mutex, passed on from rosd
    '''

    # ..........................................................................
    def __init__(self, mutex=None, level=Level.INFO):
        '''
        This initialises the ROS and calls the YAML configurer.
        '''
        self._mutex = mutex if mutex is not None else threading.Lock() 
        super().__init__("ros", None, self._mutex)
        self._log.info('setting process as high priority...')
        # set ROS as high priority
        proc = psutil.Process(os.getpid())
        proc.nice(10)
        self._config       = None
        self._active       = False
        self._closing      = False
        self._disable_leds = False
        self._arbitrator   = None
        self._controller   = None
        self._gamepad      = None
        self._motors       = None
        self._ifs          = None
        self._features     = []
        self._log.info('initialised.')

    # ..........................................................................
    def configure(self, arguments):
        '''
        Provided with a set of configuration arguments, configures ROS based on
        both KD01/KR01 standard hardware as well as optional features, the 
        latter based on devices showing up (by address) on the I²C bus. Optional
        devices are only enabled at startup time via registration of their feature
        availability.
        '''
        self._log.heading('configuration', 'configuring ros...', 
            '[1/2]' if arguments.start else '[1/1]')
        self._log.info('application log level: {}'.format(self._log.level.name))
        # configuration from command line arguments 
        self._using_mocks   = False
        self._permit_mocks  = arguments.mock
        self._enable_camera = arguments.camera # TODO
        # read YAML configuration
        _loader = ConfigLoader(self._log.level)
        _config_file = arguments.config_file if arguments.config_file is not None else 'config.yaml'
        self._config = _loader.configure(_config_file)
        # scan I2C bus
        self._log.info('scanning I²C address bus...')
        scanner = I2CScanner(self._log.level)
        self._addresses = scanner.get_int_addresses()
        _hex_addresses = scanner.get_hex_addresses()
        self._addrDict = dict(list(map(lambda x, y:(x,y), self._addresses, _hex_addresses)))
#       for i in range(len(self._addresses)):
        for _address in self._addresses:
            _device_name = self.get_device_for_address(_address)
            self._log.info('found device at I²C address 0x{:02X}: {}'.format(_address, _device_name) + Style.RESET_ALL)
            # TODO look up address and make assumption about what the device is
        # establish basic subsumption components
        self._log.info('configure application messaging...')
        self._message_factory = MessageFactory(self._log.level)
        self._message_bus = MessageBus(self._log.level)
        self._log.info('configuring system clock...')
        self._clock = Clock(self._config, self._message_bus, self._message_factory, Level.WARN)
        self.add_feature(self._clock)

        # standard devices ...........................................
        self._log.info('configure default features...')

        self._log.info('configure CPU temperature check...')
        _temperature_check = Temperature(self._config, self._clock, self._log.level)
        if _temperature_check.get_cpu_temperature() > 0:
            self.add_feature(_temperature_check)
        else:
            self._log.warning('no support for CPU temperature.')

        motors_enabled = not arguments.no_motors and ( 0x15 in self._addresses )
        if motors_enabled: # then configure motors
            self._log.debug(Fore.CYAN + Style.BRIGHT + '-- ThunderBorg available at 0x15' + Style.RESET_ALL)
            _motor_configurer = MotorConfigurer(self._config, self._clock, self._log.level)
            self._motors = _motor_configurer.get_motors()
            self.add_feature(self._motors)
            self._set_feature_available('motors', motors_enabled)
        elif self._permit_mocks:
            self._using_mocks   = True
            self._log.debug(Fore.RED + Style.BRIGHT + '-- no ThunderBorg available, using mocks.' + Style.RESET_ALL)
            from mock.motor_configurer import MockMotorConfigurer
            _motor_configurer = MockMotorConfigurer(self._config, self._clock, self._log.level)
            self._motors = _motor_configurer.get_motors()
            self.add_feature(self._motors)
            self._set_feature_available('motors', motors_enabled)

        ifs_available = ( 0x0E in self._addresses )
        if ifs_available:
            self._log.info('configuring integrated front sensor...')
            self._ifs = IntegratedFrontSensor(self._config, self._clock, self._log.level)
            self.add_feature(self._ifs)
        elif self._permit_mocks:
            self._using_mocks   = True
            self._log.info('integrated front sensor not available; loading mock sensor.')
            from mock.ifs import MockIntegratedFrontSensor
            self._ifs = MockIntegratedFrontSensor(self._message_bus, exit_on_complete=False, level=self._log.level)
            self._message_bus.set_ifs(self._ifs)
            self.add_feature(self._ifs)
        else:
            self._ifs = None
            self._log.warning('no integrated front sensor available.')

#       ultraborg_available = ( 0x36 in self._addresses )
#       if ultraborg_available:
#           self._log.debug(Fore.CYAN + Style.BRIGHT + '-- UltraBorg available at 0x36.' + Style.RESET_ALL)
#       else:
#           self._log.debug(Fore.RED + Style.BRIGHT + '-- no UltraBorg available at 0x36.' + Style.RESET_ALL)
#       self._set_feature_available('ultraborg', ultraborg_available)

#       # optional devices ...........................................
        self._log.info('configure optional features...')
        self._gamepad_enabled = arguments.gamepad and self._config['ros'].get('gamepad').get('enabled')
        
#       # the 5x5 RGB Matrix is at 0x74 for port, 0x77 for starboard
#       rgbmatrix5x5_stbd_available = ( 0x74 in self._addresses )
#       if rgbmatrix5x5_stbd_available:
#           self._log.debug(Fore.CYAN + Style.BRIGHT + '-- RGB Matrix available at 0x74.' + Style.RESET_ALL)
#       else:
#           self._log.debug(Fore.RED + Style.BRIGHT + '-- no RGB Matrix available at 0x74.' + Style.RESET_ALL)
#       self._set_feature_available('rgbmatrix5x5_stbd', rgbmatrix5x5_stbd_available)
#       rgbmatrix5x5_port_available = ( 0x77 in self._addresses )
#       if rgbmatrix5x5_port_available:
#           self._log.debug(Fore.CYAN + Style.BRIGHT + '-- RGB Matrix available at 0x77.' + Style.RESET_ALL)
#       else:
#           self._log.debug(Fore.RED + Style.BRIGHT + '-- no RGB Matrix available at 0x77.' + Style.RESET_ALL)
#       self._set_feature_available('rgbmatrix5x5_port', rgbmatrix5x5_port_available)

#       if rgbmatrix5x5_stbd_available or rgbmatrix5x5_port_available:
#           self._log.info('configure rgbmatrix...')
#           self._rgbmatrix = RgbMatrix(Level.INFO)
#           self.add_feature(self._rgbmatrix) # FIXME this is added twice

#       # ............................................
#       # the 11x7 LED matrix is at 0x75 for starboard, 0x77 for port. The latter
#       # conflicts with the RGB LED matrix, so both cannot be used simultaneously.
#       matrix11x7_stbd_available = ( 0x75 in self._addresses )
#       if matrix11x7_stbd_available:
#           self._log.debug(Fore.CYAN + Style.BRIGHT + '-- 11x7 Matrix LEDs available at 0x75.' + Style.RESET_ALL)
#       else:
#           self._log.debug(Fore.RED + Style.BRIGHT + '-- no 11x7 Matrix LEDs available at 0x75.' + Style.RESET_ALL)
#       self._set_feature_available('matrix11x7_stbd', matrix11x7_stbd_available)

#       # device availability ........................................

#       bno055_available = ( 0x28 in self._addresses )
#       if bno055_available:
#           self._log.info('configuring BNO055 9DoF sensor...')
#           self._bno055 = BNO055(self._config, self.get_message_queue(), Level.INFO)
#       else:
#           self._log.debug(Fore.RED + Style.BRIGHT + 'no BNO055 orientation sensor available at 0x28.' + Style.RESET_ALL)
#       self._set_feature_available('bno055', bno055_available)

#       # NOTE: the default address for the ICM20948 is 0x68, but this conflicts with the PiJuice
#       icm20948_available = ( 0x69 in self._addresses )
#       if icm20948_available:
#           self._log.debug(Fore.CYAN + Style.BRIGHT + 'ICM20948 available at 0x69.' + Style.RESET_ALL)
#       else:
#           self._log.debug(Fore.RED + Style.BRIGHT + 'no ICM20948 available at 0x69.' + Style.RESET_ALL)
#       self._set_feature_available('icm20948', icm20948_available)

#       lsm303d_available = ( 0x1D in self._addresses )
#       if lsm303d_available:
#           self._log.debug(Fore.CYAN + Style.BRIGHT + 'LSM303D available at 0x1D.' + Style.RESET_ALL)
#       else:
#           self._log.debug(Fore.RED + Style.BRIGHT + 'no LSM303D available at 0x1D.' + Style.RESET_ALL)
#       self._set_feature_available('lsm303d', lsm303d_available)
#   
#       vl53l1x_available = ( 0x29 in self._addresses )
#       if vl53l1x_available:
#           self._log.debug(Fore.CYAN + Style.BRIGHT + 'VL53L1X available at 0x29.' + Style.RESET_ALL)
#       else:
#           self._log.debug(Fore.RED + Style.BRIGHT + 'no VL53L1X available at 0x29.' + Style.RESET_ALL)
#       self._set_feature_available('vl53l1x', vl53l1x_available)

#       as7262_available = ( 0x49 in self._addresses )
#       if as7262_available:
#           self._log.debug(Fore.CYAN + Style.BRIGHT + '-- AS7262 Spectrometer available at 0x49.' + Style.RESET_ALL)
#       else:
#           self._log.debug(Fore.RED + Style.BRIGHT + '-- no AS7262 Spectrometer available at 0x49.' + Style.RESET_ALL)
#       self._set_feature_available('as7262', as7262_available)

#       pijuice_available = ( 0x68 in self._addresses )
#       if pijuice_available:
#           self._log.debug(Fore.CYAN + Style.BRIGHT + 'PiJuice hat available at 0x68.' + Style.RESET_ALL)
#       else:
#           self._log.debug(Fore.RED + Style.BRIGHT + 'no PiJuice hat available at 0x68.' + Style.RESET_ALL)
#       self._set_feature_available('pijuice', pijuice_available)

        self._log.info(Fore.YELLOW + 'configure subsumption support...')

        # configure the MessageQueue, Controller and Arbitrator
        self._log.info('configuring message queue...')
        self._queue = MessageQueue(self._message_bus, self._log.level)
        self._message_bus.add_handler(Message, self._queue.handle)
        self._log.info('configuring controller...')
        self._controller = Controller(self._config, self._ifs, self._motors, self._callback_shutdown, self._log.level)
        self._log.info('configuring arbitrator...')
        self._arbitrator = Arbitrator(self._config, self._queue, self._controller, self._log.level)
        self._log.info('configured.')

    # ..........................................................................
    def _set_feature_available(self, name, value):
        '''
            Sets a feature's availability to the boolean value.
        '''
        self._log.debug(Fore.BLUE + Style.BRIGHT + '-- set feature available. name: \'{}\' value: \'{}\'.'.format(name, value))
        self.set_property('features', name, value)

    # ..........................................................................
    def get_device_for_address(self, address):
        if address == 0x0E:
            return 'RGB Potentiometer'
        elif address == 0x0F:
            return 'RGB Encoder' # default, moved to 0x16
        elif address == 0x15:
            return 'ThunderBorg'
        elif address == 0x16:
            return 'RGB Encoder'
        elif address == 0x18:
            return 'IO Expander'
        elif address == 0x48:
            return 'ADS1015'
        elif address == 0x4A:
            return 'Unknown'
        elif address == 0x74:
            return '5x5 RGB Matrix'
        elif address == 0x77:
            return '5x5 RGB Matrix (or 11x7 LED Matrix)'
        else:
            return 'Unknown'

    # ..........................................................................
    @property
    def controller(self):
        return self._controller

    # ..........................................................................
    @property
    def configuration(self):
        return self._config

    # ..........................................................................
    def get_property(self, section, property_name):
        '''
        Return the value of the named property of the application
        configuration, provided its section and property name.
        '''
        return self._config[section].get(property_name)

    # ..........................................................................
    def set_property(self, section, property_name, property_value):
        '''
        Set the value of the named property of the application
        configuration, provided its section, property name and value.
        '''
        self._log.debug(Fore.GREEN + 'set config on section \'{}\' for property key: \'{}\' to value: {}.'.format(\
                section, property_name, property_value))
        if section == 'ros':
            self._config[section].update(property_name = property_value)
        else:
            _ros = self._config['ros']
            _ros[section].update(property_name = property_value)

    # ..........................................................................
    def _set_pi_leds(self, enable):
        '''
        Enables or disables the Raspberry Pi's board LEDs.
        '''
        sudo_name = self.get_property('pi', 'sudo_name')
        # led_0_path:   '/sys/class/leds/led0/brightness'
        _led_0_path = self._config['pi'].get('led_0_path')
        _led_0 = Path(_led_0_path)
        # led_1_path:   '/sys/class/leds/led1/brightness'
        _led_1_path = self._config['pi'].get('led_1_path')
        _led_1 = Path(_led_1_path)
        if _led_0.is_file() and _led_0.is_file():
            if enable:
                self._log.info('re-enabling LEDs...')
                os.system('echo 1 | {} tee {}'.format(sudo_name,_led_0_path))
                os.system('echo 1 | {} tee {}'.format(sudo_name,_led_1_path))
            else:
                self._log.debug('disabling LEDs...')
                os.system('echo 0 | {} tee {}'.format(sudo_name,_led_0_path))
                os.system('echo 0 | {} tee {}'.format(sudo_name,_led_1_path))
        else:
            self._log.warning('could not change state of LEDs: does not appear to be a Raspberry Pi.')

    # ..........................................................................
    def _connect_gamepad(self):
        if not self._gamepad_enabled:
            self._log.info('gamepad disabled.')
            return
        if self._gamepad is None:
            self._log.info('creating gamepad...')
            try:
                self._gamepad = Gamepad(self._config, self._queue, Level.INFO)
            except GamepadConnectException as e:
                self._log.error('unable to connect to gamepad: {}'.format(e))
                self._gamepad = None
                self._gamepad_enabled = False
                self._log.info('gamepad unavailable.')
                return
        if self._gamepad is not None:
            self._log.info('enabling gamepad...')
            self._gamepad.enable()
            _count = 0
            while not self._gamepad.has_connection():
                _count += 1
                if _count == 1:
                    self._log.info('connecting to gamepad...')
                else:
                    self._log.info('gamepad not connected; re-trying... [{:d}]'.format(_count))
                self._gamepad.connect()
                time.sleep(0.5)
                if self._gamepad.has_connection() or _count > 5:
                    break

    # ..........................................................................
    def has_connected_gamepad(self):
        return self._gamepad is not None and self._gamepad.has_connection()

    # ..........................................................................
    def get_arbitrator(self):
        return self._arbitrator

    # ..........................................................................
    def add_feature(self, feature):
        '''
        Add the feature to the list of features. Features must have 
        an enable() method.
        '''
        self._features.append(feature)
        self._log.info('added feature {}.'.format(feature.name()))

    # ..........................................................................
    def _callback_shutdown(self):
        _enable_self_shutdown = self._config['ros'].get('enable_self_shutdown')
        if _enable_self_shutdown:
            self._log.critical('callback: shutting down os...')
            self.close()
            sys.exit(0)
        else:
            self._log.critical('self-shutdown disabled.')

    # ..........................................................................
    def _print_banner(self):
        '''
        Display banner on console.
        '''
        self._log.info('…')
        self._log.info('…     █▒▒▒▒▒▒▒     █▒▒▒▒▒▒     █▒▒▒▒▒▒    █▒▒ ')
        self._log.info('…     █▒▒   █▒▒   █▒▒   █▒▒   █▒▒         █▒▒ ')
        self._log.info('…     █▒▒▒▒▒▒     █▒▒   █▒▒    █▒▒▒▒▒▒    █▒▒ ')
        self._log.info('…     █▒▒  █▒▒    █▒▒   █▒▒         █▒▒       ')
        self._log.info('…     █▒▒   █▒▒    █▒▒▒▒▒▒     █▒▒▒▒▒▒    █▒▒ ')
        self._log.info('…')

    # ..........................................................................
    def run(self):
        '''
        This first disables the Pi's status LEDs, establishes the
        message queue arbitrator, the controller, enables the set
        of features, then starts the main OS loop.
        '''
        super(AbstractTask, self).run()
        loop_count = 0
        self._print_banner()

        self._disable_leds = self._config['pi'].get('disable_leds')
        if self._disable_leds:
            # disable Pi LEDs since they may be distracting
            self._set_pi_leds(False)

        _main_loop_freq_hz = self._config['ros'].get('main_loop_freq_hz')
        self._main_loop_rate = Rate(_main_loop_freq_hz)

#       __enable_player = self._config['ros'].get('enable_player')
#       if __enable_player:
#           self._log.info('configuring sound player...')
#           self._player = Player(Level.INFO)
#       else:
#           self._player = None

#       i2c_slave_address = config['ros'].get('i2c_master').get('device_id') # i2c hex address of I2C slave device

#       vl53l1x_available = True # self.get_property('features', 'vl53l1x')
#       ultraborg_available = True # self.get_property('features', 'ultraborg')
#       if vl53l1x_available and ultraborg_available:
#           self._log.critical('starting scanner tool...')
#           self._lidar = Lidar(self._config, Level.INFO)
#           self._lidar.enable()
#       else:
#           self._log.critical('lidar scanner tool does not have necessary dependencies.')
        
        # wait to stabilise features?

#       _flask_enabled = self._config['flask'].get('enabled')
#       if _flask_enabled:
#           self._log.info('starting flask web server...')
#           self.configure_web_server()
#       else:
#           self._log.info('not starting flask web server (suppressed from command line).')

        # bluetooth gamepad controller
#       if self._gamepad_enabled:
#           self._connect_gamepad()


#       _wait_for_button_press = self._config['ros'].get('wait_for_button_press')
#       self._controller.set_standby(_wait_for_button_press)

        # begin main loop ..............................

#       self._log.info('enabling bno055 sensor...')
#       self._bno055.enable()

#       self._bumpers.enable()

#       self._indicator = Indicator(Level.INFO)
        # add indicator as message listener
#       self._queue.add_listener(self._indicator)

#       self._log.info(Fore.MAGENTA + 'enabling integrated front sensor...')
#       self._ifs.enable() 
#       self._log.info('starting info thread...')
#       self._info.start()

#       self._log.info('starting blinky thread...')
#       self._rgbmatrix.enable(DisplayType.RANDOM)

        self._log.info('enabling features...')
        for feature in self._features:
            self._log.info('enabling feature {}...'.format(feature.name()))
            feature.enable()

        self._log.notice('Press Ctrl-C to exit.')
        self._log.info('begin main os loop.\r')

        # enable arbitrator tasks (normal functioning of robot)
#       self._arbitrator.start()

        _main_loop_counter = itertools.count()
        self._active = True
        while self._active:
            # the timing of this loop is inconsequential; it exists solely as a keep-alive.
            self._log.debug('[{:d}] main loop...'.format(next(_main_loop_counter)))
            self._main_loop_rate.wait()
    
        if not self._closing:
            self._log.warning('closing following loop...')
            self.close()
        # end main ...................................

    # ..........................................................................
    def emergency_stop(self):
        '''
        Stop immediately, something has hit the top feelers.
        '''
        self._motors.stop()
        self._log.info(Fore.RED + Style.BRIGHT + 'emergency stop: contact on upper feelers.')

    # ..........................................................................
    def send_message(self, message):
        '''
        Send the Message into the MessageQueue.
        '''
#       self._queue.add(message)
        raise Exception('unsupported')

    # ..........................................................................
    def enable(self):
        super(AbstractTask, self).enable()

    # ..........................................................................
    def disable(self):
        super(AbstractTask, self).disable()

    # ..........................................................................
    def close(self):
        '''
        This sets the ROS back to normal following a session.
        '''
        if self._closing:
            # this also gets called by the arbitrator so we ignore that
            self._log.info('already closing.')
            return
        else:
            self._active = False
            self._closing = True
            self._log.info(Style.BRIGHT + 'closing...')
            if self._gamepad:
                self._gamepad.close() 
            if self._motors:
                self._motors.close()
            if self._ifs:
                self._ifs.close() 

            # close features
            for feature in self._features:
                self._log.info('closing feature {}...'.format(feature.name()))
                feature.close()
            self._log.info('finished closing features.')
            if self._arbitrator:
                self._arbitrator.disable()
                self._arbitrator.close()
#               self._arbitrator.join(timeout=1.0)
            if self._controller:
                self._controller.disable()
            super().close()

            if self._disable_leds:
                # restore LEDs
                self._set_pi_leds(True)
         
#           GPIO.cleanup()
#           self._log.info('joining main thread...')
#           self.join(timeout=0.5)
            self._log.info('os closed.')
            sys.stderr = DevNull()
            sys.exit(0)

# ==============================================================================

# ..............................................................................
def parse_args():
    '''
    Parses the command line arguments and return the resulting args object.
    Help is available via '--help', '-h', or calling the script with no arguments.
    '''
    _log = Logger('parse-args', Level.INFO)
    _log.debug('parsing...')
    formatter = lambda prog: argparse.HelpFormatter(prog,max_help_position=60)
    parser = argparse.ArgumentParser(formatter_class=formatter,
            description='Provides command line control of the ROS application.', \
            epilog='This script may be executed by rosd (ros daemon) or run directly from the command line.')
    parser.add_argument('--configure',      '-c', action='store_true', help='run configuration (included by -s)')
    parser.add_argument('--start',          '-s', action='store_true', help='start ros')
    parser.add_argument('--no-motors',      '-n', action='store_true', help='disable motors')
    parser.add_argument('--gamepad',        '-g', action='store_true', help='enable bluetooth gamepad control')
    parser.add_argument('--camera',         '-C', action='store_true', help='enable camera if installed')
    parser.add_argument('--mock',           '-m', action='store_true', help='permit mocked libraries (when not on a Pi)')
    parser.add_argument('--config-file',    '-f', help='use alternative configuration file')
    parser.add_argument('--level',          '-l', help='specify logging level \'DEBUG\'|\'INFO\'|\'WARN\'|\'ERROR\' (default: \'INFO\')')
    try:
        args = parser.parse_args()
        _log.debug('parsed arguments: {}\n'.format(args))
#       print_banner()
        if not args.configure and not args.start:
            print('')
            parser.print_help()
            return None
        else:
            return args

    except NotImplementedError as nie:
        _log.error('unrecognised log level \'{}\': {}'.format(args.level, nie))
        _log.error('exit on error.')
        sys.exit(1)
    except Exception as e:
        _log.error('error parsing command line arguments: {}\n{}'.format(e, traceback.format_exc()))
        _log.error('exit on error.')
        sys.exit(1)

# exception handler ............................................................

def signal_handler(signal, frame):
    global _ros
    print('\nsignal handler    :' + Fore.MAGENTA + Style.BRIGHT + ' INFO  : Ctrl-C caught: exiting...' + Style.RESET_ALL)
    if _ros:
        _ros.close()
    print(Fore.MAGENTA + 'exit.' + Style.RESET_ALL)
    sys.stderr = DevNull()
#   sys.exit()
    sys.exit(0)

# main .........................................................................

_ros = None

def main(argv):
    global _ros

    _log = Logger("main", Level.INFO)
    signal.signal(signal.SIGINT, signal_handler)

    try:
        _args = parse_args()
        if _args == None:
            print('')
            _log.info(Fore.CYAN + 'arguments: no action.')
        else:
            _level = Level.from_str(_args.level) if _args.level != None else Level.INFO
            _log.level = _level
            _log.info('arguments: {}'.format(_args))
            _ros = ROS(level=_level)
            if _args.configure or _args.start:
                _ros.configure(_args)
                if not _args.start:
                    _log.info('configure only: ' + Fore.YELLOW + 'specify the -s argument to start ros.')
            if _args.start:
                _ros.start()

    except KeyboardInterrupt:
        print(Fore.CYAN + Style.BRIGHT + 'caught Ctrl-C; exiting...')
    except Exception:
        print(Fore.RED + Style.BRIGHT + 'error starting ros: {}'.format(traceback.format_exc()) + Style.RESET_ALL)
        if _ros:
            _ros.close()
    finally:
        _log.info('exit.')

# call main ....................................................................
if __name__== "__main__":
    main(sys.argv[1:])

# prevent Python script from exiting abruptly
#signal.pause()

#EOF
