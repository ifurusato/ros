#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# Copyright 2020 by Murray Altheim. All rights reserved. This file is part of
# the Robot Operating System project and is released under the "Apache Licence, 
# Version 2.0". Please see the LICENSE file included as part of this package.
#
# author:   Murray Altheim
# created:  2019-12-23
# modified: 2020-03-12
#
#        1         2         3         4         5         6         7         8         9         C
#234567890123456789012345678901234567890123456789012345678901234567890123456789012345678901234567890

# ..............................................................................
import os, sys, psutil, signal, time, itertools, logging, yaml, threading, traceback
from pathlib import Path
from colorama import init, Fore, Style
init()

#import RPi.GPIO as GPIO
#rom lib.import_gpio import *

from lib.logger import Level, Logger
from lib.rate import Rate
from lib.devnull import DevNull
from lib.event import Event
from lib.message import Message
from lib.abstract_task import AbstractTask 
from lib.fsm import FiniteStateMachine
from lib.message import Message
from lib.message_bus import MessageBus
from lib.message_factory import MessageFactory
from lib.queue import MessageQueue
from lib.config_loader import ConfigLoader
from lib.i2c_scanner import I2CScanner
from lib.clock import Clock

from lib.temperature import Temperature

#from lib.arbitrator import Arbitrator
#from lib.controller import Controller
#from lib.indicator import Indicator
#from lib.gamepad import Gamepad, GamepadConnectException

# standard features:
from lib.motor_configurer import MotorConfigurer
from lib.motors import Motors
from lib.ifs import IntegratedFrontSensor
#from lib.lidar import Lidar
#from lib.matrix import Matrix
#from lib.rgbmatrix import RgbMatrix, DisplayType
#from lib.bno055 import BNO055

led_0_path = '/sys/class/leds/led0/brightness'
led_1_path = '/sys/class/leds/led1/brightness'

_level = Level.INFO

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
    def __init__(self, mutex=None):
        '''
        This initialises the ROS and calls the YAML configurer.
        '''
        self._mutex = mutex if mutex is not None else threading.Lock() 
        super().__init__("ros", None, self._mutex)
        self._log.info('setting process as high priority...')
        # set ROS as high priority
        proc = psutil.Process(os.getpid())
        proc.nice(10)
        self._active       = False
        self._closing      = False
        self._disable_leds = False
        self._motors       = None
        self._arbitrator   = None
        self._controller   = None
        self._gamepad      = None
        self._features     = []
        self._log.info('initialised.')
        self._configure()

    # ..........................................................................
    def _configure(self):
        '''
        Configures ROS based on both KR01 standard hardware as well as
        optional features, the latter based on devices showing up (by 
        address) on the I²C bus. Optional devices are only enabled at
        startup time via registration of their feature availability.
        '''
        self._log.info('configuring...')
        # read YAML configuration
        _level = Level.INFO
        _loader = ConfigLoader(_level)
        filename = 'config.yaml'
        self._config = _loader.configure(filename)
        # scan I2C bus
        self._log.info('scanning I²C address bus...')
        scanner = I2CScanner(Level.WARN)
        self._addresses = scanner.get_addresses()
        hexAddresses = scanner.getHexAddresses()
        self._addrDict = dict(list(map(lambda x, y:(x,y), self._addresses, hexAddresses)))
        for i in range(len(self._addresses)):
            self._log.info(Fore.BLACK + Style.DIM + 'found device at address: {}'.format(hexAddresses[i]) + Style.RESET_ALL)
        # establish basic subsumption components
        self._log.info('configure subsumption foundation...')
        self._message_factory = MessageFactory(_level)
        self._message_bus = MessageBus(_level)
        self._log.info('configuring system clock...')
        self._clock = Clock(self._config, self._message_bus, self._message_factory, Level.WARN)
        self.add_feature(self._clock)

        # standard devices ...........................................
        self._log.info('configure default features...')

        self._log.info('configure CPU temperature check...')
        _temperature_check = Temperature(self._config, self._clock, _level)
        self.add_feature(_temperature_check)

        thunderborg_available = ( 0x15 in self._addresses )
        if thunderborg_available: # then configure motors
            self._log.debug(Fore.CYAN + Style.BRIGHT + '-- ThunderBorg available at 0x15' + Style.RESET_ALL)
            _motor_configurer = MotorConfigurer(self._config, self._clock, _level)
            self._motors = _motor_configurer.get_motors()
            self.add_feature(self._motors)
        else:
            self._log.debug(Fore.RED + Style.BRIGHT + '-- no ThunderBorg available at 0x15.' + Style.RESET_ALL)
        self._set_feature_available('thunderborg', thunderborg_available)

        ifs_available = ( 0x0E in self._addresses )
        if ifs_available:
            self._log.info('configuring integrated front sensor...')
            self._ifs = IntegratedFrontSensor(self._config, self._clock, _level)
            self.add_feature(self._ifs)
        else:
            self._log.info('integrated front sensor not available; loading mock sensor.')
            from mock.mock_ifs import MockIntegratedFrontSensor
            self._ifs = MockIntegratedFrontSensor(self._config, self._clock, _level)
            self.add_feature(self._ifs)

#       ultraborg_available = ( 0x36 in self._addresses )
#       if ultraborg_available:
#           self._log.debug(Fore.CYAN + Style.BRIGHT + '-- UltraBorg available at 0x36.' + Style.RESET_ALL)
#       else:
#           self._log.debug(Fore.RED + Style.BRIGHT + '-- no UltraBorg available at 0x36.' + Style.RESET_ALL)
#       self._set_feature_available('ultraborg', ultraborg_available)

#       # optional devices ...........................................
        self._log.info('configure optional features...')
        self._gamepad_enabled = self._config['ros'].get('gamepad').get('enabled')

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
        self._log.info('configured.')

    # ..........................................................................
    def _set_feature_available(self, name, value):
        '''
            Sets a feature's availability to the boolean value.
        '''
        self._log.debug(Fore.BLUE + Style.BRIGHT + '-- set feature available. name: \'{}\' value: \'{}\'.'.format(name, value))
        self.set_property('features', name, value)

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
                self._queue = MessageQueue(Level.INFO)
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

        self._log.info('enabling features...')
        for feature in self._features:
            self._log.info('enabling feature {}...'.format(feature.name()))
            feature.enable()

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

        # configure the Controller and Arbitrator
#       self._log.info('configuring controller...')
#       self._controller = Controller(self._config, self._ifs, self._motors, self._callback_shutdown, Level.INFO)

#       self._log.info('configuring arbitrator...')
#       self._arbitrator = Arbitrator(self._config, self._queue, self._controller, Level.WARN)

#       _flask_enabled = self._config['flask'].get('enabled')
#       if _flask_enabled:
#           self._log.info('starting flask web server...')
#           self.configure_web_server()
#       else:
#           self._log.info('not starting flask web server (suppressed from command line).')

        # bluetooth gamepad controller
#       if self._gamepad_enabled:
#           self._connect_gamepad()

        self._log.warning('Press Ctrl-C to exit.')

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

        # enable arbitrator tasks (normal functioning of robot)

        _main_loop_freq_hz = self._config['ros'].get('main_loop_freq_hz')
        self._log.info('begin main os loop.')
#       self._log.info('begin main os loop at {:5.2f}Hz.'.format(_main_loop_freq_hz))
        self._main_loop_rate = Rate(_main_loop_freq_hz)
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

_ros = None

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
def main(argv):
    global _ros

    signal.signal(signal.SIGINT, signal_handler)

    try:
        _ros = ROS()
        _ros.start()
    except KeyboardInterrupt:
        print(Fore.CYAN + Style.BRIGHT + 'caught Ctrl-C; exiting...')
    except Exception:
        print(Fore.RED + Style.BRIGHT + 'error starting ros: {}'.format(traceback.format_exc()) + Style.RESET_ALL)
        if _ros:
            _ros.close()

# call main ....................................................................
if __name__== "__main__":
    main(sys.argv[1:])

# prevent Python script from exiting abruptly
#signal.pause()

#EOF
