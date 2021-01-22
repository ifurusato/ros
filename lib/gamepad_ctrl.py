#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# Copyright 2020 by Murray Altheim. All rights reserved. This file is part of
# the Robot Operating System project and is released under the "Apache Licence,
# Version 2.0". Please see the LICENSE file included as part of this package.
#
# author:   Murray Altheim
# created:  2020-08-05
# modified: 2020-10-26
#

import sys, itertools, time, threading
import datetime as dt
from colorama import init, Fore, Style
init()

from lib.logger import Logger, Level
from lib.enums import Color, Orientation
from lib.event import Event
from lib.gamepad import Gamepad
#from lib.message import Message
#from lib.matrix import Matrix
#from lib.behaviours_v2 import Behaviours
from lib.cruise import CruiseBehaviour
from lib.rate import Rate
 
# ..............................................................................
class GamepadController():
    '''
    This is a controller for the Gamepad, and also acts as a message 
    consumer by implementing the queue.add(Message) method.

    :param config:          the application configuration
    :param queue:           the message queue
    :param pid_motor_ctrl:  the PID motor controller
    :param ifs:             the integrated front sensor    (optional)
    :param video:           the video capture              (optional)
    :param blob:            the blob detector              (optional)
    :param matrix11x7_available:  a flag indicating the 11x7 LED matrix display is available,
                            determining if the 'light' feature is available.
    :param level:           the log level
    :param close_callback:  a callback executed upon closing the controller
    '''
    def __init__(self, config, queue, pid_motor_ctrl, ifs, video, blob, matrix11x7_available, level, close_callback):
        super().__init__()
        if config is None:
            raise ValueError('null configuration argument.')
        self._log = Logger("gp-ctrl", level)
        self._config = config
        self._queue = queue
        _config = config['ros'].get('gamepad_demo').get('controller')
        self._log_to_file    = _config.get('log_to_file')
        self._log_to_console = _config.get('log_to_console')
        self._min_loop_ms    = _config.get('min_loop_time_ms') # minimum gamepad loop time (ms)
        self._hysteresis_limit = 3.0
        self._pid_motor_ctrl = pid_motor_ctrl
        self._motors = self._pid_motor_ctrl.get_motors()
        _controllers = pid_motor_ctrl.get_pid_controllers()
        self._port_pid = _controllers[0]
        self._stbd_pid = _controllers[1]
        self._ifs            = ifs
        self._video          = video
        self._blob           = blob
#       self._behaviours = Behaviours(config, self._pid_motor_ctrl, level)
        if matrix11x7_available:
            self._port_light = Matrix(Orientation.PORT, Level.INFO)
            self._stbd_light = Matrix(Orientation.STBD, Level.INFO)
        else:
            self._port_light = None
            self._stbd_light = None
        self._close_callback = close_callback
        # get ready...
        self._counter        = itertools.count()
        self._cruise_behaviour = None
        self._monitor_thread = None
        self._pid_enabled    = False
        self._enabled        = False
        self._lights_on      = False
        self._queue.add_consumer(self)
        self._start_time     = dt.datetime.now()
        self._log.info('ready.')

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
    @property
    def enabled(self):
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
        if self._video is not None:
            if enabled:
                self._log.info(Fore.GREEN + Style.BRIGHT + 'START VIDEO')
                self._video.start()
                self.set_led_color(Color.BLACK) # so it doesn't show up on video
            else:
                self._log.info(Fore.GREEN + Style.BRIGHT + 'STOP VIDEO')
                if self._video is not None:
                    self._video.stop()
#               self.set_led_color(Color.DARK_GREEN)
                self.set_led_show_battery(True)
        else:
            self._log.warning('video is not available.')

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
                    raise Exception('monitor unsupported.')
                    self._monitor_thread = threading.Thread(name='gamepad-ctrl', target=GamepadController._monitor, args=[self, lambda: self._pid_enabled ], daemon=True)
                    self._monitor_thread.start()
                self._port_pid.enable()
                self._stbd_pid.enable()

    # ......................................................
    def add(self, message):
        if not self._enabled:
            return
        message.number = next(self._counter)
        event = message.event
        if event is Event.CLOCK_TICK:
#           self._log.debug('TICK RECEIVED: {};\tcount: {:5.2f}'.format(event.description, message.value))
            _priority_message = self._queue.next()
            if _priority_message and not _priority_message.event.is_ignoreable:
                self.handle_message(_priority_message)

        elif event is Event.CLOCK_TOCK:
#           self._log.debug(Fore.YELLOW + Style.NORMAL + 'TOCK RECEIVED: {};\tcount: {:5.2f}'.format(event.description, message.value))
            pass

        else:
#           self._log.debug(Fore.WHITE + Style.DIM + 'message RECEIVED with event type: {};\tcount: {:5.2f}'.format(event.description, message.value))
            pass

    # ......................................................
    def _hysteresis(self, value):
        '''
        If the value is less than the hysteresis limit returns zero, otherwise the argument.
        This assumes the midpoint of the 0-255 range is 127.0.
        '''
#       return value
        return 127.0 if abs(value - 127.0) < self._hysteresis_limit else value

    # ......................................................
    def handle_message(self, message):
        message.number = next(self._counter)
        # show elapsed time
        _delta = dt.datetime.now() - self._start_time
        _elapsed_ms = int(_delta.total_seconds() * 1000)
        # we want to limit the messages to 1/5ms, so if elapsed time is less than that we'll just pad it out 
        # set pad to -1 to disable feature
        if _elapsed_ms < self._min_loop_ms:
            time.sleep((self._min_loop_ms - _elapsed_ms)/1000)
            _delta = dt.datetime.now() - self._start_time
            _elapsed_ms = int(_delta.total_seconds() * 1000)
#           self._log.debug('elapsed since last message: {}ms (padded)'.format(_elapsed_ms))
            self._log.debug(Fore.MAGENTA + 'handling message #{}: priority {}: {};\telapsed: {}ms'.format(message.number, message.priority, message.description, _elapsed_ms) + " (padded)")
        else:
#           self._log.debug('elapsed since last message: {}ms'.format(_elapsed_ms))
            self._log.debug(Fore.MAGENTA + 'handling message #{}: priority {}: {};\telapsed: {}ms'.format(message.number, message.priority, message.description, _elapsed_ms) + "")

        # ........................................
        event = message.event

        if event is Event.INFRARED_PORT_SIDE:
            self._log.debug(Fore.RED + Style.BRIGHT   + 'event: {};\tvalue: {:5.2f}cm'.format(event.description, message.value))

        elif event is Event.INFRARED_PORT:
            self._log.debug(Fore.RED + Style.BRIGHT   + 'event: {};\tvalue: {:5.2f}cm'.format(event.description, message.value))

#       elif event is Event.INFRARED_CNTR:
#           _cruising_velocity = self._behaviours.get_cruising_velocity()
#           _distance = message.value
#           _clamped_distance = Behaviours.clamp(_distance, 20.0, 100.0)
#           _mapped_velocity = Behaviours.remap(_clamped_distance, 20.0, 100.0, 0.0, _cruising_velocity)
#           self._log.info(Fore.BLUE + Style.NORMAL  + 'event: {};'.format(event.description) + Fore.YELLOW + '\tmapped velocity: {:5.2f}cm'.format(message.value ))
#           self._log.info(Fore.BLUE + Style.NORMAL + '_distance: {:5.2f}\t'.format(_distance) + Style.BRIGHT + '\tcruising velocity: {:5.2f}cm;'.format(_cruising_velocity) \
#                   + Fore.YELLOW + Style.NORMAL + '\tvelocity: {:5.2f}'.format(_mapped_velocity))
#           pids = self._pid_motor_ctrl.set_max_velocity(_mapped_velocity)

        elif event is Event.INFRARED_CNTR:
            self._log.debug(Fore.BLUE + Style.BRIGHT  + 'event: {};\tvalue: {:5.2f}cm'.format(event.description, message.value))

        elif event is Event.INFRARED_STBD:
            self._log.debug(Fore.GREEN + Style.BRIGHT + 'event: {};\tvalue: {:5.2f}cm'.format(event.description, message.value))

        elif event is Event.INFRARED_STBD_SIDE:
            self._log.debug(Fore.GREEN + Style.BRIGHT + 'event: {};\tvalue: {:5.2f}cm'.format(event.description, message.value))

        # ........................................

        elif event is Event.BUMPER_PORT:
            self._log.info(Fore.RED + Style.BRIGHT   + 'event: {};\tvalue: {:d}'.format(event.description, message.value))
        elif event is Event.BUMPER_CNTR:
            self._log.info(Fore.BLUE + Style.BRIGHT  + 'event: {};\tvalue: {:d}'.format(event.description, message.value))
        elif event is Event.BUMPER_STBD:
            self._log.info(Fore.GREEN + Style.BRIGHT + 'event: {};\tvalue: {:d}'.format(event.description, message.value))

        elif event is Event.PORT_VELOCITY:
            if not self._port_pid.enabled:
                self._port_pid.enable()
#           if message.value == 0: # on push of button
#           _value = message.value # with no hysteresis
            _value = self._hysteresis(message.value)
            _velocity = Gamepad.convert_range(_value)
            self._log.debug(Fore.RED + 'PORT: {};\tvalue: {:>5.2f}; velocity: {:>5.2f};'.format(event.description, _value, _velocity))
#           self._motors.set_motor(Orientation.PORT, _velocity)
            self._port_pid.velocity = _velocity * 100.0

        elif event is Event.PORT_THETA:
#           if message.value == 0: # on push of button
            _velocity = -1 * Gamepad.convert_range(message.value)
            self._log.debug('{};\tvalue: {:>5.2f}'.format(event.description, _velocity))

        elif event is Event.STBD_VELOCITY:
            if not self._stbd_pid.enabled:
                self._stbd_pid.enable()
#           if message.value == 0: # on push of button
#           _value = message.value # with no hysteresis
            _value = self._hysteresis(message.value)
            _velocity = Gamepad.convert_range(_value)
            self._log.info(Fore.GREEN + 'STBD: {};\tvalue: {:>5.2f}; velocity: {:>5.2f};'.format(event.description, _value, _velocity))
#           self._motors.set_motor(Orientation.STBD, _velocity)
            self._stbd_pid.velocity = _velocity * 100.0

        elif event is Event.STBD_THETA:
#           if message.value == 0: # on push of button
            _velocity = -1 * Gamepad.convert_range(message.value)
            self._log.debug('{};\tvalue: {:>5.2f}'.format(event.description, _velocity))

        elif event is Event.SHUTDOWN:
            if message.value == 1: # shutdown on push of button
                self._log.info('SHUTDOWN event.')
                self._close()

        elif event is Event.STANDBY:
            self._log.info(Fore.YELLOW + Style.DIM + 'STANDBY event: {};\tvalue: {:d}'.format(event.description, message.value))
        elif event is Event.HALT:
            self._log.info(Fore.RED + Style.BRIGHT + 'HALT event: {};\tvalue: {:d}'.format(event.description, message.value))
        elif event is Event.BRAKE:
            self._log.info(Fore.RED + Style.BRIGHT + 'BRAKE event: {};\tvalue: {:d}'.format(event.description, message.value))
            if message.value == 1: # shutdown on push of button
                self._enable_pid(not self._port_pid.enabled)
                
        elif event is Event.STOP:
            self._log.info(Fore.RED + Style.BRIGHT + 'STOP event: {};\tvalue: {:d}'.format(event.description, message.value))
        elif event is Event.ROAM:
#           if message.value == 0:
#               self._behaviours.roam()
            pass
        elif event is Event.SNIFF:
#           if message.value == 0:
#               self._behaviours.one_meter()
            pass
        elif event is Event.NO_ACTION:
            self._log.info(Fore.BLACK + Style.DIM + 'NO_ACTION event: {};\tvalue: {:d}'.format(event.description, message.value))

        elif event is Event.VIDEO:
            if message.value == 0:
                if self._video:
                    if self._video.active:
                        self._log.info(Fore.GREEN + Style.DIM + 'STOP VIDEO event: {};\tvalue: {:d}'.format(event.description, message.value))
                        self._enable_video(False)
                    else:
                        self._log.info(Fore.GREEN + Style.DIM + 'START VIDEO event: {};\tvalue: {:d}'.format(event.description, message.value))
                        self._enable_video(True)
    #               time.sleep(0.5) # debounce
                else:
                    self._log.warning('video not available.')

        elif event is Event.EVENT_L2:
            if message.value == 0:
                self._log.info(Fore.GREEN + Style.DIM + 'BLOB_SENSOR event: {};\tvalue: {:d}'.format(event.description, message.value))
                self._capture_blob()
#               time.sleep(0.5) # debounce
        elif event is Event.LIGHTS:
            if message.value == 0:
                self._enable_lights(not self._lights_on)

        elif event is Event.EVENT_R1:
            if message.value == 0:
                self._log.info(Fore.MAGENTA + 'EVENT_R1 event (cruise): {}'.format(event.description))
                if self._cruise_behaviour is None:
                    # create a new CruiseBehaviour
                    self._cruise_behaviour = CruiseBehaviour(self._config, self._pid_motor_ctrl, self._ifs, Level.INFO)
                    self._queue.add_consumer(self._cruise_behaviour)
                    self._cruise_behaviour.enable()
                    self._log.info(Fore.MAGENTA + 'enabled cruise.')
                else:
                    self._queue.remove_consumer(self._cruise_behaviour)
                    self._cruise_behaviour.disable()
#                   self._cruise_behaviour.close()
                    self._cruise_behaviour = None
                    self._log.info(Fore.MAGENTA + 'disabled cruise.')

        else:
            self._log.debug(Fore.RED + 'other event: {}'.format(event.description))
            pass

        self._start_time = dt.datetime.now()

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


# EOF
