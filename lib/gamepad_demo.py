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

import sys, itertools, time, threading, traceback
import datetime as dt
from enum import Enum
from colorama import init, Fore, Style
init()

try:
    from evdev import InputDevice, categorize, ecodes
except ImportError:
    sys.exit("This script requires the evdev module\nInstall with: sudo pip3 install evdev")

from lib.config_loader import ConfigLoader
from lib.logger import Logger, Level
from lib.i2c_scanner import I2CScanner
from lib.enums import Color, Orientation
from lib.event import Event
from lib.message import Message, MessageFactory
from lib.queue import MessageQueue
from lib.gamepad import Gamepad
from lib.lux import Lux
from lib.compass import Compass
#rom lib.blob import BlobSensor
from lib.video import Video
from lib.indicator import Indicator
from lib.ifs import IntegratedFrontSensor
from lib.batterycheck import BatteryCheck
from lib.matrix import Matrix
from lib.behaviours_v2 import Behaviours
from lib.rate import Rate
from lib.motors_v2 import Motors
from lib.pid_ctrl import PIDMotorController
 
# ..............................................................................
class GamepadController():
    '''
       While this implements the queue.add(Message) method, this is a
       controller for the Gamepad demo.
    '''
    def __init__(self, config, motor_controller, video, blob, matrix11x7_available, level, close_callback):
        super().__init__()
        if config is None:
            raise ValueError('null configuration argument.')
        self._log = Logger("mock-queue", level)
        self._config = config['ros'].get('gamepad_demo').get('controller')
        self._log_to_file    = self._config.get('log_to_file')
        self._log_to_console = self._config.get('log_to_console')
        self._min_loop_ms    = self._config.get('min_loop_time_ms') # minimum gamepad loop time (ms)
        self._motor_controller = motor_controller
        self._motors = self._motor_controller.get_motors()
        _controllers = motor_controller.get_pid_controllers()
        self._port_pid = _controllers[0]
        self._stbd_pid = _controllers[1]
        self._video          = video
        self._blob           = blob
        self._behaviours = Behaviours(config, self._port_pid, self._stbd_pid, None, level)
        self._counter = itertools.count()
        if matrix11x7_available:
            self._port_light = Matrix(Orientation.PORT, Level.INFO)
            self._stbd_light = Matrix(Orientation.STBD, Level.INFO)
        else:
            self._port_light = None
            self._stbd_light = None
        self._close_callback = close_callback
        self._monitor_thread = None
        self._pid_enabled    = False
        self._enabled        = False
        self._lights_on      = False
        self._consumers      = []
        self._start_time     = dt.datetime.now()
        self._log.info('ready.')

    # ..........................................................................
    def add_consumer(self, consumer):
        '''
            Add a consumer to the optional list of message consumers.
        '''
        return self._consumers.append(consumer)

    # ..........................................................................
    def enable(self):
        self._enabled = True

    # ..........................................................................
    def disable(self):
        self._enabled = False
#       self._behaviours.disable()

    # ..........................................................................
    def _close(self):
        self.disable()
        self._close_callback()

    # ..........................................................................
    def is_enabled(self):
        return self._enabled

    # ..........................................................................
    def set_led_color(self, color):
        self._log.info('set LED color to {}.'.format(color))
        self._motors.set_led_show_battery(False)
        self._motors.set_led_color(color)

    # ..........................................................................
    def set_led_show_battery(self, enabled):
        self._log.info('set LED show battery to {}.'.format(enabled))
        self._motors.set_led_show_battery(enabled)

    # ..........................................................................
    def _enable_video(self, enabled):
        if enabled:
            self._log.info(Fore.GREEN + Style.BRIGHT + 'START VIDEO')
            self._video.start()
            self.set_led_color(Color.BLACK) # so it doesn't show up on video
        else:
            self._log.info(Fore.GREEN + Style.BRIGHT + 'STOP VIDEO')
            if self._video is not None:
                self._video.stop()
#           self.set_led_color(Color.DARK_GREEN)
            self.set_led_show_battery(True)

    # ..........................................................................
    def _capture_blob(self):
        if self._blog:
            self._log.info('capture blob image.')
#           self.set_led_color(Color.BLACK) # so it doesn't show up on video
            self._blob.capture()
#           time.sleep(0.5)
#           self.set_led_show_battery(True)
            self._log.info('blob capture complete.')
        else:
            self._log.info('blob capture not enabled.')

    # ..........................................................................
    def _enable_lights(self, enabled):
        if self._port_light and self._stbd_light:
            if enabled:
                self._port_light.light()
                self._stbd_light.light()
            else:
                self._port_light.clear()
                self._stbd_light.clear()
        self._lights_on = enabled

    # ..........................................................................
    def _enable_pid(self, enabled):
        if self._port_pid.enabled:
            self._pid_enabled = False
            self._port_pid.disable()
            self._stbd_pid.disable()
        else:
            if self._monitor_thread is None:
                self._pid_enabled = True
                if self._log_to_file or self._log_to_console:
                    # if logging to file and/or console start monitor thread
                    self._monitor_thread = threading.Thread(target=GamepadController._monitor, args=[self, lambda: self._pid_enabled ])
                    self._monitor_thread.start()
            self._port_pid.enable()
            self._stbd_pid.enable()

    # ..........................................................................
    def _monitor(self, f_is_enabled):
        '''
            A 20Hz loop that prints PID statistics to the log while enabled. Note that this loop
            is not synchronised with the two PID controllers, which each have their own loop.
        '''
        _indent = '                                                    '
        self._log.info('PID monitor header:\n' \
            + _indent + 'name   : description\n' \
            + _indent + 'kp     : proportional constant\n' \
            + _indent + 'ki     : integral constant\n' \
            + _indent + 'kd     : derivative constant\n' \
            + _indent + 'p_cp   : port proportial value\n' \
            + _indent + 'p_ci   : port integral value\n' \
            + _indent + 'p_cd   : port derivative value\n' \
            + _indent + 'p_lpw  : port last power\n' \
            + _indent + 'p_cpw  : port current motor power\n' \
            + _indent + 'p_spwr : port set power\n' \
            + _indent + 'p_cvel : port current velocity\n' \
            + _indent + 'p_stpt : port velocity setpoint\n' \
            + _indent + 's_cp   : starboard proportial value\n' \
            + _indent + 's_ci   : starboard integral value\n' \
            + _indent + 's_cd   : starboard derivative value\n' \
            + _indent + 's_lpw  : starboard proportional value\n' \
            + _indent + 's_cpw  : starboard integral value\n' \
            + _indent + 's_spw  : starboard derivative value\n' \
            + _indent + 's_cvel : starboard current velocity\n' \
            + _indent + 's_stpt : starboard velocity setpoint\n' \
            + _indent + 'p_stps : port encoder steps\n' \
            + _indent + 's_stps : starboard encoder steps')

        if self._log_to_file:
            self._file_log = Logger("pid", Level.INFO, log_to_file=True)
            # write header
            self._file_log.file("kp|ki|kd|p_cp|p_ci|p_cd|p_lpw|p_cpw|p_spwr|p_cvel|p_stpt|s_cp|s_ci|s_cd|s_lpw|s_cpw|s_spw|s_cvel|s_stpt|p_stps|s_stps|")

            self._log.info(Fore.GREEN + 'starting PID monitor...')
        _rate = Rate(20)
        while f_is_enabled():
            kp, ki, kd, p_cp, p_ci, p_cd, p_last_power, p_current_motor_power, p_power, p_current_velocity, p_setpoint, p_steps = self._port_pid.stats
            _x, _y, _z, s_cp, s_ci, s_cd, s_last_power, s_current_motor_power, s_power, s_current_velocity, s_setpoint, s_steps = self._stbd_pid.stats
            _msg = ('{:7.4f}|{:7.4f}|{:7.4f}|{:7.4f}|{:7.4f}|{:7.4f}|{:5.2f}|{:5.2f}|{:5.2f}|{:<5.2f}|{:>5.2f}|{:d}|{:7.4f}|{:7.4f}|{:7.4f}|{:5.2f}|{:5.2f}|{:5.2f}|{:<5.2f}|{:>5.2f}|{:d}|').format(\
                    kp, ki, kd, p_cp, p_ci, p_cd, p_last_power, p_current_motor_power, p_power, p_current_velocity, p_setpoint, p_steps, \
                    s_cp, s_ci, s_cd, s_last_power, s_current_motor_power, s_power, s_current_velocity, s_setpoint, s_steps)
            _p_hilite = Style.BRIGHT if p_power > 0.0 else Style.NORMAL
            _s_hilite = Style.BRIGHT if s_power > 0.0 else Style.NORMAL
            _msg2 = (Fore.RED+_p_hilite+'{:7.4f}|{:7.4f}|{:7.4f}|{:<5.2f}|{:<5.2f}|{:<5.2f}|{:>5.2f}|{:d}'+Fore.GREEN+_s_hilite+'|{:7.4f}|{:7.4f}|{:7.4f}|{:5.2f}|{:5.2f}|{:<5.2f}|{:<5.2f}|{:d}|').format(\
                    p_cp, p_ci, p_cd, p_last_power, p_power, p_current_velocity, p_setpoint, p_steps, \
                    s_cp, s_ci, s_cd, s_last_power, s_power, s_current_velocity, s_setpoint, s_steps)
            _rate.wait()
            if self._log_to_file:
                self._file_log.file(_msg)
            if self._log_to_console:
                self._log.info(_msg2)
        self._log.info('PID monitor stopped.')

    # ......................................................
    def add(self, message):
        message.set_number(next(self._counter))
        if not self._enabled:
            self._log.warning('queue disabled: message ignored #{}: priority {}: {}'.format(message.get_number(), message.get_priority(), message.get_description()))
            return

        # show elapsed time
        _delta = dt.datetime.now() - self._start_time
        _elapsed_ms = int(_delta.total_seconds() * 1000)
        # we want to limit the messages to 1/5ms, so if elapsed time is less than that we'll just pad it out 
        # set pad to -1 to disable feature
        if _elapsed_ms < self._min_loop_ms:
            time.sleep((self._min_loop_ms - _elapsed_ms)/1000)
            _delta = dt.datetime.now() - self._start_time
            _elapsed_ms = int(_delta.total_seconds() * 1000)
            self._log.debug('elapsed since last message: {}ms (padded)'.format(_elapsed_ms))
        else:
            self._log.debug('elapsed since last message: {}ms'.format(_elapsed_ms))

        self._log.debug('added message #{}: priority {}: {}'.format(message.get_number(), message.get_priority(), message.get_description()))
        event = message.get_event()

        if event is Event.INFRARED_PORT_SIDE:
            self._log.info(Fore.RED + Style.BRIGHT   + 'event: {};\tvalue: {:d}'.format(event.description, message.get_value()))
        elif event is Event.INFRARED_PORT:
            self._log.info(Fore.RED + Style.BRIGHT   + 'event: {};\tvalue: {:d}'.format(event.description, message.get_value()))
        elif event is Event.INFRARED_CNTR:
            self._log.info(Fore.BLUE + Style.BRIGHT  + 'event: {};\tvalue: {:d}'.format(event.description, message.get_value()))
        elif event is Event.INFRARED_STBD:
            self._log.info(Fore.GREEN + Style.BRIGHT + 'event: {};\tvalue: {:d}'.format(event.description, message.get_value()))
        elif event is Event.INFRARED_STBD_SIDE:
            self._log.info(Fore.GREEN + Style.BRIGHT + 'event: {};\tvalue: {:d}'.format(event.description, message.get_value()))
        elif event is Event.BUMPER_PORT:
            self._log.info(Fore.RED + Style.BRIGHT   + 'event: {};\tvalue: {:d}'.format(event.description, message.get_value()))
        elif event is Event.BUMPER_CNTR:
            self._log.info(Fore.BLUE + Style.BRIGHT  + 'event: {};\tvalue: {:d}'.format(event.description, message.get_value()))
        elif event is Event.BUMPER_STBD:
            self._log.info(Fore.GREEN + Style.BRIGHT + 'event: {};\tvalue: {:d}'.format(event.description, message.get_value()))

        elif event is Event.PORT_VELOCITY:
#           if message.get_value() == 0: # on push of button
            _value = message.get_value()
            _velocity = Gamepad.convert_range(_value)
#           self._log.info(Fore.WHITE + Style.BRIGHT + 'PORT: {};\tvalue: {:>5.2f}; velocity: {:>5.2f};'.format(event.description, _value, _velocity))
#           self._motors.set_motor(Orientation.PORT, _velocity)
            self._port_pid.velocity = _velocity * 100.0

        elif event is Event.PORT_THETA:
#           if message.get_value() == 0: # on push of button
            _velocity = -1 * Gamepad.convert_range(message.get_value())
            self._log.debug('{};\tvalue: {:>5.2f}'.format(event.description, _velocity))

        elif event is Event.STBD_VELOCITY:
#           if message.get_value() == 0: # on push of button
            _value = message.get_value()
            _velocity = Gamepad.convert_range(_value)
#           self._log.info(Fore.WHITE + Style.BRIGHT + 'STBD: {};\tvalue: {:>5.2f}; velocity: {:>5.2f};'.format(event.description, _value, _velocity))
#           self._motors.set_motor(Orientation.STBD, _velocity)
            self._stbd_pid.velocity = _velocity * 100.0

        elif event is Event.STBD_THETA:
#           if message.get_value() == 0: # on push of button
            _velocity = -1 * Gamepad.convert_range(message.get_value())
            self._log.debug('{};\tvalue: {:>5.2f}'.format(event.description, _velocity))

        elif event is Event.SHUTDOWN:
            if message.get_value() == 1: # shutdown on push of button
                self._log.info('SHUTDOWN event.')
                self._close()

        elif event is Event.STANDBY:
            self._log.info(Fore.YELLOW + Style.DIM + 'STANDBY event: {};\tvalue: {:d}'.format(event.description, message.get_value()))
        elif event is Event.HALT:
            self._log.info(Fore.RED + Style.BRIGHT + 'HALT event: {};\tvalue: {:d}'.format(event.description, message.get_value()))
        elif event is Event.BRAKE:
            self._log.info(Fore.RED + Style.BRIGHT + 'BRAKE event: {};\tvalue: {:d}'.format(event.description, message.get_value()))
            if message.get_value() == 1: # shutdown on push of button
                self._enable_pid(not self._port_pid.enabled)
                
        elif event is Event.STOP:
            self._log.info(Fore.RED + Style.BRIGHT + 'STOP event: {};\tvalue: {:d}'.format(event.description, message.get_value()))
        elif event is Event.ROAM:
            if message.get_value() == 0:
                self._behaviours.roam()
        elif event is Event.SNIFF:
            if message.get_value() == 0:
                self._behaviours.one_meter()
        elif event is Event.NO_ACTION:
            self._log.info(Fore.BLACK + Style.DIM + 'NO_ACTION event: {};\tvalue: {:d}'.format(event.description, message.get_value()))

        elif event is Event.VIDEO:
            if message.get_value() == 0:
                if self._video.active:
                    self._log.info(Fore.GREEN + Style.DIM + 'STOP VIDEO event: {};\tvalue: {:d}'.format(event.description, message.get_value()))
                    self._enable_video(False)
                else:
                    self._log.info(Fore.GREEN + Style.DIM + 'START VIDEO event: {};\tvalue: {:d}'.format(event.description, message.get_value()))
                    self._enable_video(True)
#               time.sleep(0.5) # debounce
        elif event is Event.EVENT_L2:
            if message.get_value() == 0:
                self._log.info(Fore.GREEN + Style.DIM + 'BLOB_SENSOR event: {};\tvalue: {:d}'.format(event.description, message.get_value()))
                self._capture_blob()
#               time.sleep(0.5) # debounce
        elif event is Event.LIGHTS:
            if message.get_value() == 0:
                self._enable_lights(not self._lights_on)

        elif event is Event.EVENT_R1:
            self._log.info(Fore.RED + 'EVENT_R1 event: {}'.format(event.description))
        else:
            self._log.info(Fore.RED + 'other event: {}'.format(event.description))
            pass

        # we're finished, now add to any consumers
        for consumer in self._consumers:
            consumer.add(message);

        self._start_time = dt.datetime.now()


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
        self._enable_ifs      = self._config.get('enable_ifs')
        self._enable_compass  = self._config.get('enable_compass')
        self._message_factory = MessageFactory(level)
        self._motors = Motors(_config, None, Level.INFO)
#       self._motor_controller = SimpleMotorController(self._motors, Level.INFO)
        self._motor_controller = PIDMotorController(_config, self._motors, Level.WARN)
        # i2c scanner, let's us know if certain devices are available
        _i2c_scanner = I2CScanner(Level.WARN)
        _addresses = _i2c_scanner.getAddresses()
        ltr559_available = ( 0x23 in _addresses )
        ''' Availability of displays:
            The 5x5 RGB Matrix is at 0x74 for port, 0x77 for starboard.
            The 11x7 LED matrix is at 0x75 for starboard, 0x77 for port. The latter
            conflicts with the RGB LED matrix, so both cannot be used simultaneously.
            We check for either the 0x74 address to see if RGB Matrix displays are 
            used, OR for 0x75 to assume a pair of 11x7 Matrix displays are being used.
        '''
        rgbmatrix5x5_stbd_available = ( 0x74 in _addresses ) # not used yet
        matrix11x7_stbd_available   = ( 0x75 in _addresses ) # used as camera lighting

#       self._blob      = BlobSensor(_config, self._motors, Level.INFO)
        self._blob      = None
        self._lux       = Lux(Level.INFO) if ltr559_available else None
        self._video     = Video(_config, self._lux, matrix11x7_stbd_available, Level.INFO)
        self._queue     = GamepadController(_config, self._motor_controller, self._video, self._blob, matrix11x7_stbd_available, Level.INFO, self._close_demo_callback)

        # attempt to find the gamepad
        self._gamepad = Gamepad(_config, self._queue, self._message_factory, Level.INFO)

        self._indicator = Indicator(Level.INFO)
        if self._enable_compass:
            self._compass = Compass(_config, self._queue, self._indicator, Level.INFO)
            self._video.set_compass(self._compass)

        self._log.info('starting battery check thread...')
        self._battery_check = BatteryCheck(_config, self._queue, self._message_factory, Level.INFO)

        if self._enable_ifs:
            self._log.info('integrated front sensor enabled.')
            self._ifs  = IntegratedFrontSensor(_config, self._queue, Level.INFO)
            # add indicator as message consumer
            self._queue.add_consumer(self._indicator)
        else:
            self._ifs  = None
            self._log.info('integrated front sensor disabled.')
        self._enabled = False
        self._log.info('connecting gamepad...')
        self._gamepad.connect()
        self._log.info('ready.')

    # ..........................................................................
    def is_enabled(self):
        return self._enabled

    # ..........................................................................
    def enable(self):
        if self._enabled:
            self._log.warning('already enabled.')
            return
        self._log.info('enabling...')
        self._queue.enable()
        self._gamepad.enable()
        if self._enable_compass:
            self._compass.enable()
        self._battery_check.enable()
        if self._enable_ifs:
            self._ifs.enable()
#       while self._queue.is_enabled():
#           time.sleep(1.0)
#       self._log.info('exited loop.         zzzzzzzzzzzzzzzzz ')
        self._enabled = True
        self._log.info('enabled.')

    # ..........................................................................
    def disable(self):
        if not self._enabled:
            self._log.warning('already disabled.')
            return
        self._log.info('disabling...')
        self._battery_check.disable()
        if self._enable_compass:
            self._compass.disable()
        if self._enable_ifs:
            self._ifs.disable()
        self._motor_controller.disable()
        self._gamepad.disable()
        self._enabled = False
        self._log.info('disabled.')

    # ..........................................................................
    def _close_demo_callback(self):
        self._log.info('close demo callback...')
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
        self._motor_controller.close()
        self._gamepad.close()
        self._log.info('closed.')

## main .........................................................................
#def main(argv):
#
#    try:
#
#        _gamepad_demo = GamepadDemo(Level.INFO)
#        _gamepad_demo.enable()
##       sys.exit(0)
#
#    except KeyboardInterrupt:
#        print(Fore.RED + 'caught Ctrl-C; exiting...' + Style.RESET_ALL)
#        sys.exit(0)
#    except Exception:
#        print(Fore.RED + Style.BRIGHT + 'error processing gamepad events: {}'.format(traceback.format_exc()) + Style.RESET_ALL)
#        sys.exit(1)
#
#
## call main ....................................................................
#if __name__== "__main__":
#    main(sys.argv[1:])

# EOF
