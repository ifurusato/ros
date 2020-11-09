#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# Copyright 2020 by Murray Altheim. All rights reserved. This file is part of
# the Robot Operating System project and is released under the "Apache Licence,
# Version 2.0". Please see the LICENSE file included as part of this package.
#
# author:   Murray Altheim
# created:  2020-08-05
# modified: 2020-10-18
#
# This is a test class that interprets the signals arriving from the 8BitDo N30
# Pro Gamepad, a paired Bluetooth device. The result is passed on to a 
# mocked MessageQueue, which passes a filtered subset of those messages on to a 
# SimpleMotorController. The result is tele-robotics, i.e., a remote-controlled 
# robot.
#

import sys, threading # TEMP
from colorama import init, Fore, Style
init()

from lib.config_loader import ConfigLoader
from lib.logger import Logger, Level
from lib.i2c_scanner import I2CScanner
from lib.queue import MessageQueue
from lib.message_factory import MessageFactory
#from lib.message import Message
from lib.gamepad import Gamepad
from lib.gamepad_ctrl import GamepadController
from lib.clock import Clock
from lib.lux import Lux
#from lib.compass import Compass
#rom lib.blob import BlobSensor
#from lib.video import Video
#from lib.matrix import Matrix
#from lib.indicator import Indicator
from lib.ifs import IntegratedFrontSensor
from lib.batterycheck import BatteryCheck
from lib.motors_v2 import Motors
from lib.pid_ctrl import PIDMotorController


# ..............................................................................
class GamepadDemo():

    def __init__(self, level):
        super().__init__()
        _loader      = ConfigLoader(Level.INFO)
        filename     = 'config.yaml'
        _config      = _loader.configure(filename)
        self._log = Logger("gamepad-demo", level)
        self._log.header('gamepad-demo','Configuring Gamepad...',None)
        self._config = _config['ros'].get('gamepad_demo')
        self._enable_ifs       = self._config.get('enable_ifs')
        self._enable_compass   = self._config.get('enable_compass')
        self._enable_indicator = self._config.get('enable_indicator')
        self._message_factory  = MessageFactory(level)
        self._motors = Motors(_config, None, Level.INFO)
#       self._motor_controller = SimpleMotorController(self._motors, Level.INFO)
        self._pid_motor_ctrl = PIDMotorController(_config, self._motors, Level.INFO)
        # i2c scanner, let's us know if certain devices are available
        _i2c_scanner = I2CScanner(Level.WARN)
        _addresses = _i2c_scanner.getAddresses()
        ltr559_available = ( 0x23 in _addresses )
        '''
        Availability of displays:
        The 5x5 RGB Matrix is at 0x74 for port, 0x77 for starboard.
        The 11x7 LED matrix is at 0x75 for starboard, 0x77 for port. The latter
        conflicts with the RGB LED matrix, so both cannot be used simultaneously.
        We check for either the 0x74 address to see if RGB Matrix displays are 
        used, OR for 0x75 to assume a pair of 11x7 Matrix displays are being used.
        '''
#       rgbmatrix5x5_stbd_available = ( 0x74 in _addresses ) # not used yet
#       matrix11x7_stbd_available   = ( 0x75 in _addresses ) # used as camera lighting
        matrix11x7_stbd_available = False

#       self._blob       = BlobSensor(_config, self._motors, Level.INFO)
        self._blob       = None
        self._lux        = Lux(Level.INFO) if ltr559_available else None
        self._video      = None
#       self._video      = Video(_config, self._lux, matrix11x7_stbd_available, Level.INFO)

        # in this application the gamepad controller is the message queue
        self._queue = MessageQueue(self._message_factory, Level.INFO)

        self._clock = Clock(_config, self._queue, self._message_factory, Level.INFO)

        # attempt to find the gamepad
        self._gamepad = Gamepad(_config, self._queue, self._message_factory, Level.INFO)

#       if self._enable_indicator:
#           self._indicator = Indicator(Level.INFO)
#       if self._enable_compass:
#           self._compass = Compass(_config, self._queue, self._indicator, Level.INFO)
#           self._video.set_compass(self._compass)

        self._log.info('starting battery check thread...')
        self._battery_check = BatteryCheck(_config, self._queue, self._message_factory, Level.INFO)

        if self._enable_ifs:
            self._log.info('integrated front sensor enabled.')
            self._ifs = IntegratedFrontSensor(_config, self._queue, self._message_factory, Level.INFO)
            # add indicator as message consumer
            if self._enable_indicator:
                self._queue.add_consumer(self._indicator)
        else:
            self._ifs  = None
            self._log.info('integrated front sensor disabled.')

        self._ctrl = GamepadController(_config, self._queue, self._pid_motor_ctrl, self._ifs, self._video, self._blob, matrix11x7_stbd_available, Level.INFO, self._close_demo_callback)

        self._enabled = False
        self._log.info('connecting gamepad...')
        self._gamepad.connect()
        self._log.info('ready.')

    # ..........................................................................
    def get_motors(self):
        return self._motors

    # ..........................................................................
    @property
    def enabled(self):
        return self._enabled

    # ..........................................................................
    def enable(self):
        if self._enabled:
            self._log.warning('already enabled.')
            return
        self._log.info('enabling...')
        self._gamepad.enable()
        self._clock.enable()
#       if self._enable_compass:
#           self._compass.enable()
        self._battery_check.enable()
        if self._enable_ifs:
            self._ifs.enable()
        self._ctrl.enable()
        self._enabled = True
        self._log.info('enabled.')

    # ..........................................................................
    def get_thread_position(self, thread):
        frame = sys._current_frames().get(thread.ident, None)
        if frame:
            return frame.f_code.co_filename, frame.f_code.co_name, frame.f_code.co_firstlineno

    # ..........................................................................
    def disable(self):
        if not self._enabled:
            self._log.warning('already disabled.')
            return
        self._log.info('disabling...')
        self._enabled = False
        self._clock.disable()
        self._battery_check.disable()
#       if self._enable_compass:
#           self._compass.disable()
        if self._enable_ifs:
            self._ifs.disable()
        self._pid_motor_ctrl.disable()
        self._gamepad.disable()

        for thread in threading.enumerate():
            self._log.info(Fore.GREEN + 'thread "{}" is alive? {}; is daemon? {}\t😡'.format(thread.name, thread.is_alive(), thread.isDaemon()))
            if thread is not None:
                _position = self.get_thread_position(thread)
                if _position:
                    self._log.info(Fore.GREEN + '    thread "{}" filename: {}; co_name: {}; first_lineno: {}'.format(thread.name, _position[0], _position[1], _position[2]))
                else:
                    self._log.info(Fore.GREEN + '    thread "{}" position null.'.format(thread.name))
            else:
                self._log.info(Fore.GREEN + '    null thread.')

        self._log.info('disabled.')

    # ..........................................................................
    def _close_demo_callback(self):
        self._log.info(Fore.MAGENTA + 'close demo callback...')
#       self._queue.disable()
        self.disable()
        self.close()

    # ..........................................................................
    def close(self):
        if self._enabled:
            self.disable()
        self._log.info('closing...')
        if self._enable_ifs:
            self._ifs.close()
        self._pid_motor_ctrl.close()
        self._gamepad.close()
        self._log.info('closed.')

# EOF
