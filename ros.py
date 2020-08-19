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
import os, sys, signal, time, logging, yaml, threading, traceback
from colorama import init, Fore, Style
init()

#import RPi.GPIO as GPIO
from lib.import_gpio import *

from lib.logger import Level, Logger
from lib.devnull import DevNull
from lib.event import Event
from lib.message import Message
from lib.abstract_task import AbstractTask 
from lib.fsm import FiniteStateMachine
from lib.queue import MessageQueue
from lib.config_loader import ConfigLoader
from lib.configurer import Configurer
from lib.arbitrator import Arbitrator
from lib.controller import Controller
from lib.batlevel import BatteryLevelIndicator
from lib.indicator import Indicator
from lib.gamepad import Gamepad

#from lib.player import Player
#from lib.lidar import Lidar
#from lib.rgbmatrix import RgbMatrix

# GPIO Setup .....................................
#GPIO.setwarnings(False)
#GPIO.setmode(GPIO.BCM)

led_0_path = '/sys/class/leds/led0/brightness'
led_1_path = '/sys/class/leds/led1/brightness'

_level = Level.INFO

# import RESTful Flask Service
from flask_wrapper import FlaskWrapperService

# ==============================================================================

# ROS ..........................................................................
class ROS(AbstractTask):
    '''
        Extends AbstractTask as a Finite State Machine (FSM) basis of a Robot 
        Operating System (ROS) or behaviour-based system (BBS), including 
        spawning the various tasks and an Arbitrator as separate threads, 
        inter-communicating over a common message queue.
    
        This establishes a message queue, an Arbitrator and a Controller, as
        well as an optional RESTful flask-based web service.
    
        The message queue receives Event-containing messages, which are passed 
        on to the Arbitrator, whose job it is to determine the highest priority 
        action to execute for that task cycle.

        Example usage:

            try:
                _ros = ROS()
                _ros.start()
            except Exception:
                _ros.close()

      
        There is also a rosd linux daemon, which can be used to start, enable
        and disable ros (actually via its Arbitrator).
    '''

    # ..........................................................................
    def __init__(self):
        '''
            This initialises the ROS and calls the YAML configurer.
        '''
        self._queue = MessageQueue(Level.INFO)
        self._mutex = threading.Lock()
        super().__init__("ros", self._queue, None, None, self._mutex)
        self._log.info('initialising...')
        self._active        = False
        self._closing       = False
        self._disable_leds  = False
#       self._switch        = None
        self._motors        = None
        self._arbitrator    = None
        self._controller    = None
        self._gamepad       = None
#       self._flask_wrapper = None
        # read YAML configuration
        _loader = ConfigLoader(Level.INFO)
        filename = 'config.yaml'
        self._config = _loader.configure(filename)
        self._gamepad_enabled = self._config['ros'].get('gamepad').get('enabled')
        # import available features
        self._features = []
        _configurer = Configurer(self, Level.INFO)
        _configurer.scan()
        self._log.info('initialised.')


    # ..........................................................................
    def get_message_queue(self):
        return self._queue


    # ..........................................................................
    def get_controller(self):
        return self._controller


    # ..........................................................................
    def get_configuration(self):
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
        self._log.debug(Fore.GREEN + 'set config on section \'{}\' for property key: \'{}\' to value: {}.'.format(section, property_name, property_value))
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
        led_0_path = self._config['pi'].get('led_0_path')
        led_1_path = self._config['pi'].get('led_1_path')
        if enable:
            self._log.info('re-enabling LEDs...')
            os.system('echo 1 | {} tee {}'.format(sudo_name,led_0_path))
            os.system('echo 1 | {} tee {}'.format(sudo_name,led_1_path))
        else:
            self._log.debug('disabling LEDs...')
            os.system('echo 0 | {} tee {}'.format(sudo_name,led_0_path))
            os.system('echo 0 | {} tee {}'.format(sudo_name,led_1_path))


    # ..........................................................................
    def _connect_gamepad(self):
        if not self._gamepad_enabled:
            self._log.info('gamepad disabled.')
            return
        if self._gamepad is None:
            self._log.info('creating gamepad...')
            self._gamepad = Gamepad(self._config, self._queue, Level.INFO)
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
    def run(self):
        '''
            This first disables the Pi's status LEDs, establishes the
            message queue arbitrator, the controller, enables the set
            of features, then starts the main OS loop.
        '''
        super(AbstractTask, self).run()
        loop_count = 0
        # display banner!
        _banner = '\n' \
                  'ros\n' \
                  'ros                         █▒▒▒▒▒▒▒     █▒▒▒▒▒▒     █▒▒▒▒▒▒    █▒▒  \n' \
                + 'ros                         █▒▒   █▒▒   █▒▒   █▒▒   █▒▒         █▒▒  \n' \
                + 'ros                         █▒▒▒▒▒▒     █▒▒   █▒▒    █▒▒▒▒▒▒    █▒▒  \n' \
                + 'ros                         █▒▒  █▒▒    █▒▒   █▒▒         █▒▒        \n' \
                + 'ros                         █▒▒   █▒▒    █▒▒▒▒▒▒     █▒▒▒▒▒▒    █▒▒  \n' \
                + 'ros\n'
        self._log.info(_banner)

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

#       vl53l1x_available = False # self.get_property('features', 'vl53l1x')
#       ultraborg_available = False # self.get_property('features', 'ultraborg')
#       if vl53l1x_available and ultraborg_available:
#           self._log.critical('starting scanner tool...')
#           self._lidar = Lidar(self._config, self._player, Level.INFO)
#           self._lidar.enable()
#       else:
#           self._log.critical('scanner tool does not have necessary dependencies.')
        
#       self._ifs = IntegratedFrontSensor(self._config, self._queue, Level.INFO)
    
        # wait to stabilise features?

        # configure the Controller and Arbitrator
        self._log.info('configuring controller...')
        self._controller = Controller(self._config, self._ifs, self._motors, self._callback_shutdown, Level.INFO)

        self._log.info('configuring arbitrator...')
        self._arbitrator = Arbitrator(self._config, self._queue, self._controller, Level.WARN)

        _flask_enabled = self._config['flask'].get('enabled')
        if _flask_enabled:
            self._log.info('starting flask web server...')
            self.configure_web_server()
        else:
            self._log.info('not starting flask web server (suppressed from command line).')

        # bluetooth gamepad controller
        if self._gamepad_enabled:
            self._connect_gamepad()

        self._log.warning('Press Ctrl-C to exit.')

        _wait_for_button_press = self._config['ros'].get('wait_for_button_press')
        self._controller.set_standby(_wait_for_button_press)

        # begin main loop ..............................

        self._log.info('starting battery check thread...')
        self._ble = BatteryLevelIndicator(Level.INFO)
        self._ble.enable()

        self._log.info('starting button thread...')
        self._button.start()

#       self._log.info('enabling bno055 sensor...')
#       self._bno055.enable()

#       self._bumpers.enable()

        self._indicator = Indicator(Level.INFO)
        # add indicator as message consumer
        self._queue.add_consumer(self._indicator)

        self._log.info('enabling integrated front sensor...')
        self._ifs.enable() 
#       self._log.info('starting info thread...')
#       self._info.start()

#       self._log.info('starting blinky thread...')
#       self._rgbmatrix.enable(DisplayType.RANDOM)

        # enable arbitrator tasks (normal functioning of robot)

        main_loop_delay_ms = self._config['ros'].get('main_loop_delay_ms')
        self._log.info('begin main os loop with {:d}ms delay.'.format(main_loop_delay_ms))
        _loop_delay_sec = main_loop_delay_ms / 1000
        _main_loop_count = 0
        self._arbitrator.start()
        self._active = True
        while self._active:
#           The sensors and the flask service sends messages to the message queue,
#           which forwards those messages on to the arbitrator, which chooses the
#           highest priority message to send on to the controller. So the timing
#           of this loop is inconsequential; it exists solely as a keep-alive.
            _main_loop_count += 1
            self._log.info(Fore.BLACK + Style.DIM + '[{:d}] main loop...'.format(_main_loop_count))
            time.sleep(_loop_delay_sec)
            # end application loop .........................
    
        if not self._closing:
            self._log.warning('closing following loop...')
            self.close()
        # end main ...................................


    # ..........................................................................
    def configure_web_server(self):
        '''
            Start flask web server.
        '''
        try:
            self._mutex.acquire()
            self._log.info('starting web service...')
            self._flask_wrapper = FlaskWrapperService(self._queue, self._controller)
            self._flask_wrapper.start()
        except KeyboardInterrupt:
            self._log.error('caught Ctrl-C interrupt.')
        finally:
            self._mutex.release()
            time.sleep(1)
            self._log.info(Fore.BLUE + 'web service started.' + Style.RESET_ALL)


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
        self._queue.add(message)


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
            if self._ble:
                self._ble.disable()

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

#           if self._flask_wrapper is not None:
#               self._flask_wrapper.close()

            super().close()

#           self._info.close()
#           self._rgbmatrix.close()
#           if self._switch:
#               self._switch.close()
#           super(AbstractTask, self).close()

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
    print('\nsignal handler    :' + Fore.MAGENTA + Style.BRIGHT + ' INFO  : Ctrl-C caught: exiting...' + Style.RESET_ALL)
    if _ros is not None:
        _ros.close()
    print(Fore.MAGENTA + 'exit.' + Style.RESET_ALL)
    sys.stderr = DevNull()
#   sys.exit()
    sys.exit(0)

def print_help():
    '''
        Displays command line help.
    '''
    print('usage: ros.py [-h (help) | -n (do not start web server)]')

# main .........................................................................

def main(argv):

    signal.signal(signal.SIGINT, signal_handler)

    try:

        _ros = ROS()
        _ros.start()

#   except KeyboardInterrupt:
#       print(Fore.CYAN + Style.BRIGHT + 'caught Ctrl-C; exiting...')
#       _ros.close()
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
