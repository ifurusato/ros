#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# Copyright 2020 by Murray Altheim. All rights reserved. This file is part of
# the Robot Operating System project and is released under the "Apache Licence,
# Version 2.0". Please see the LICENSE file included as part of this package.
#
# author:   Murray Altheim
# created:  2020-08-05
# modified: 2020-08-08
#
# This is a test class that interprets the signals arriving from the 8BitDo N30
# Pro Gamepad, a paired Bluetooth device. The result is passed on to a 
# mocked MessageQueue, which passes a filtered subset of those messages on to a 
# SimpleMotorController. The result is tele-robotics, i.e., a remote-controlled 
# robot.
#
# This requires availability of the colorama library, which can be installed via:
#
#  % sudo pip3 install colorama
#

import sys, itertools, time, traceback
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
from lib.enums import Orientation
from lib.event import Event
from lib.message import Message
from lib.queue import MessageQueue
from lib.gamepad import Gamepad
from lib.lux import Lux
from lib.video import Video
from lib.ifs import IntegratedFrontSensor
from lib.indicator import Indicator
from lib.matrix import Matrix

from lib.motors import Motors

# ..............................................................................
class SimpleMotorController():
    def __init__(self, motors, level):
        super().__init__()
        self._log = Logger("motor-ctrl", Level.INFO)
        self._port_motor = motors.get_motor(Orientation.PORT)
        self._port_motor.set_motor_power(0.0)
        self._stbd_motor = motors.get_motor(Orientation.STBD)
        self._stbd_motor.set_motor_power(0.0)
        self._log.info('ready.')

    # ..........................................................................
    def set_motor(self, orientation, value):
        if orientation is Orientation.PORT:
            self._log.info(Fore.RED + 'PORT motor: {:>5.2f}%'.format(value * 100.0))
            self._port_motor.set_motor_power(value)
        elif orientation is Orientation.STBD:
            self._log.info(Fore.GREEN + 'STBD motor: {:>5.2f}%'.format(value * 100.0))
            self._stbd_motor.set_motor_power(value)
     
# ..............................................................................
class MockMessageQueue():
    def __init__(self, motors, video, level, close_callback):
        super().__init__()
        self._log = Logger("mock-queue", level)
        self._enabled = False
        self._motors = motors
        self._counter = itertools.count()
        self._video = video
        self._close_callback = close_callback
        self._port_light = Matrix(Orientation.PORT, Level.INFO)
        self._stbd_light = Matrix(Orientation.STBD, Level.INFO)
        self._consumers = []
        self._start_time = dt.datetime.now()
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

    # ..........................................................................
    def _close(self):
        self.disable()
        self._close_callback()

    # ..........................................................................
    def is_enabled(self):
        return self._enabled

    # ..........................................................................
    def _enable_video(self, enabled):
        if enabled:
            self._log.info(Fore.GREEN + Style.BRIGHT + 'START VIDEO')
            self._video.start()
        else:
            self._log.info(Fore.GREEN + Style.BRIGHT + 'STOP VIDEO')
            if self._video is not None:
                self._video.stop()

    # ..........................................................................
    def _enable_lights(self, enabled):
        if enabled:
            self._port_light.light()
            self._stbd_light.light()
        else:
            self._port_light.clear()
            self._stbd_light.clear()

    # ......................................................
    def add(self, message):
        message.set_number(next(self._counter))
        if not self._enabled:
            self._log.warning('queue disabled: message ignored #{}: priority {}: {}'.format(message.get_number(), message.get_priority(), message.get_description()))
            return

#       self._loop_delay_ms 
        # show elapsed time
        _delta = dt.datetime.now() - self._start_time
        _elapsed_ms = int(_delta.total_seconds() * 1000)
        self._log.info(Fore.CYAN + Style.DIM + 'elapsed since last message: {}ms'.format(_elapsed_ms) + Style.DIM )
#       self._start_time = dt.datetime.now()

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

        if event is Event.PORT_VELOCITY:
#           if message.get_value() == 0: # on push of button
            _velocity = Gamepad.convert_range(message.get_value())
            self._log.debug('{};\tvalue: {:>5.2f}'.format(event.description, _velocity))
            self._motors.set_motor(Orientation.PORT, _velocity)

        elif event is Event.PORT_THETA:
#           if message.get_value() == 0: # on push of button
            _velocity = -1 * Gamepad.convert_range(message.get_value())
            self._log.debug('{};\tvalue: {:>5.2f}'.format(event.description, _velocity))

        elif event is Event.STBD_VELOCITY:
#           if message.get_value() == 0: # on push of button
            _velocity = Gamepad.convert_range(message.get_value())
            self._log.debug('{};\tvalue: {:>5.2f}'.format(event.description, _velocity))
            self._motors.set_motor(Orientation.STBD, _velocity)

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
        elif event is Event.STOP:
            self._log.info(Fore.RED + Style.BRIGHT + 'STOP event: {};\tvalue: {:d}'.format(event.description, message.get_value()))
        elif event is Event.ROAM:
            self._log.info(Fore.GREEN + Style.BRIGHT + 'ROAM event: {};\tvalue: {:d}'.format(event.description, message.get_value()))
        elif event is Event.NO_ACTION:
            self._log.info(Fore.BLACK + Style.DIM + 'NO_ACTION event: {};\tvalue: {:d}'.format(event.description, message.get_value()))

        elif event is Event.START_VIDEO:
            self._log.info(Fore.GREEN + Style.DIM + 'START VIDEO event: {};\tvalue: {:d}'.format(event.description, message.get_value()))
            if message.get_value() == 0:
                self._enable_video(True)
#               time.sleep(0.5) # debounce
        elif event is Event.STOP_VIDEO:
            self._log.info(Fore.GREEN + Style.DIM + 'STOP VIDEO event: {};\tvalue: {:d}'.format(event.description, message.get_value()))
            if message.get_value() == 0:
                self._enable_video(False)
#               time.sleep(0.5) # debounce
        elif event is Event.LIGHTS_ON:
            if message.get_value() == 0:
                self._enable_lights(True)
        elif event is Event.LIGHTS_OFF:
            if message.get_value() == 0:
                self._enable_lights(False)
        else:
            self._log.info(Fore.RED + 'other event: {}'.format(event.description))
            pass

        # we're finished, now add to any consumers
        for consumer in self._consumers:
            consumer.add(message);

        self._start_time = dt.datetime.now()


class GamepadDemo():

    def __init__(self, level):
        super().__init__()
        self._log = Logger("gamepad-demo", Level.INFO)

        _loader      = ConfigLoader(Level.INFO)
        filename     = 'config.yaml'
        _config      = _loader.configure(filename)
        self._config = _config['ros'].get('gamepad_demo')
        self._enable_ifs = self._config.get('enable_ifs')
        self._loop_delay_ms = self._config.get('loop_delay_ms')

        self._motors = Motors(_config, None, None, Level.INFO)
        self._motor_controller = SimpleMotorController(self._motors, Level.INFO)

        # i2c scanner, let's us know if certain devices are available
        _i2c_scanner = I2CScanner(Level.WARN)
        _addresses = _i2c_scanner.getAddresses()

        ltr559_available = ( 0x23 in _addresses )
        self._lux      = Lux(Level.INFO) if ltr559_available else None
        self._video    = Video(_config, self._lux, Level.INFO)
        self._queue    = MockMessageQueue(self._motor_controller, self._video, Level.INFO, self._close_demo_callback)
        if self._enable_ifs:
            self._log.info('integrated front sensor enabled.')
            self._ifs  = IntegratedFrontSensor(_config, self._queue, Level.INFO)
            _indicator = Indicator(Level.INFO)
            # add indicator as message consumer
            self._queue.add_consumer(_indicator)
        else:
            self._log.info('integrated front sensor disabled.')
            self._ifs  = None

        self._gamepad = Gamepad(_config, self._queue, Level.INFO)
        self._log.info('ready.')

    # ..........................................................................
    def enable(self):
        self._log.info('enabling...')
        self._queue.enable()
        self._gamepad.enable()
        if self._enable_ifs:
            self._ifs.enable()
#       while self._queue.is_enabled():
#           time.sleep(1.0)
#       self._log.info('exited loop.         zzzzzzzzzzzzzzzzz ')
        self._log.info('enabled.')

    # ..........................................................................
    def _close_demo_callback(self):
        self._log.info('close demo callback...')
#       self._queue.disable()
        self.disable()
        self.close()

    # ..........................................................................
    def disable(self):
        self._log.info('disabling...')
        if self._enable_ifs:
            self._ifs.disable()
        self._motors.disable()
        self._gamepad.disable()
        self._log.info('disabled.')

    # ..........................................................................
    def close(self):
        self._log.info('closing...')
        if self._enable_ifs:
            self._ifs.close()
        self._motors.close()
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
