#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# Copyright 2020-2021 by Murray Altheim. All rights reserved. This file is part
# of the Robot Operating System project, released under the MIT License. Please
# see the LICENSE file included as part of this package.
#
# A test to establish some basic values for the PID loop. This uses an IOE
# based RotaryControl for the setpoint (velocity) and an IOE Potentiometer
# to set the Kx constants.
#

import sys, time, numpy, traceback
from colorama import init, Fore, Style
init()

from lib.logger import Logger, Level
from lib.config_loader import ConfigLoader
from lib.clock import Clock
from lib.message_bus import MessageBus
from lib.message_factory import MessageFactory
from lib.motor_configurer import MotorConfigurer
from lib.motors import Motors
from lib.enums import Orientation
#from lib.gamepad import Gamepad
from lib.pid_ctrl import PIDController
from lib.ioe_pot import Potentiometer
from lib.rotary_ctrl import RotaryControl

from lib.button import Button

ROTATE                       = False # move forward or rotate in place?
ROTATE_VALUE = -1.0 if ROTATE else 1.0
# motor configuration: starboard, port or both?
ORIENTATION = Orientation.STBD    # STBD, PORT or BOTH?

_level = Level.INFO
_log = Logger('main', _level)

# ..............................................................................
def callback_method_A(value):
    global action_A
    action_A = not action_A
    _log.info('callback method fired;\t' + Fore.YELLOW + 'action A: {}'.format(action_A))

# ..............................................................................
def callback_method_B(value):
    global action_B
    action_B = not action_B
    _log.info('callback method fired;\t' + Fore.YELLOW + 'action B: {}'.format(action_B))

# ..............................................................................
def main():
    global action_A, action_B
    # initial states
    action_A = False
    action_B = True

    _loader = ConfigLoader(_level)
    _config = _loader.configure('config.yaml')

    _pin_A = 12
    _button_12 = Button(_pin_A, callback_method_A, Level.INFO)
    _log.info(Style.BRIGHT + 'press button A (connected to pin {:d}) to toggle or initiate action.'.format(_pin_A))

    _pin_B = 24
    _button_24 = Button(_pin_B, callback_method_B, Level.INFO)
    _log.info(Style.BRIGHT + 'press button B connected to pin {:d}) to exit.'.format(_pin_B))

    try:

        _log.info('creating message factory...')
        _message_factory = MessageFactory(Level.INFO)
        _log.info('creating message bus...')
        _message_bus = MessageBus(Level.DEBUG)
        _log.info('creating clock...')
        _clock = Clock(_config, _message_bus, _message_factory, Level.WARN)
        _motor_configurer = MotorConfigurer(_config, _clock, Level.INFO)
        _motors = _motor_configurer.get_motors()
      
        _limit  = 90.0
        _stbd_setpoint  = 0.0
        _port_setpoint  = 0.0
        _scaled_value   = 0.0
        _value          = 0.0
        _port_pid_ctrl  = None
        _stbd_pid_ctrl  = None

        # rotary controller
        _min_rot        = 0
        _max_rot        = 30
        _step_rot       = 1
        _rotary_ctrl = RotaryControl(_config, _min_rot, _max_rot, _step_rot, Level.WARN)

        # configure motors/PID controllers
        if ORIENTATION == Orientation.BOTH or ORIENTATION == Orientation.PORT:
            _port_motor = _motors.get_motor(Orientation.PORT)
            _port_pid_ctrl = PIDController(_config, _clock, _port_motor, level=Level.INFO)
            _port_pid_ctrl.limit = _limit
            _port_pid_ctrl.enable()
        if ORIENTATION == Orientation.BOTH or ORIENTATION == Orientation.STBD:
            _stbd_motor = _motors.get_motor(Orientation.STBD)
            _stbd_pid_ctrl = PIDController(_config, _clock, _stbd_motor, level=Level.INFO)
            _stbd_pid_ctrl.limit = _limit
            _stbd_pid_ctrl.enable()

        _max_pot = 1.0
        _min_pot = 0.0
        _pot = Potentiometer(_config, Level.WARN)
        _pot.set_output_limits(_min_pot, _max_pot)

        _motors.enable()

        try:
            while action_B:
                if action_A:
                    _log.info(Fore.BLUE + Style.BRIGHT + 'action A.')
                    action_A = False # trigger once
                    _stbd_setpoint  = 0.0
                    _port_setpoint  = 0.0

                    while action_B:
    
                        # set PID constant
                        _scaled_value = _pot.get_scaled_value(True)
#                       _log.info(Style.DIM + 'PID TUNER kp: {:8.5f}   ================ '.format(_scaled_value))
                        if ORIENTATION == Orientation.BOTH or ORIENTATION == Orientation.PORT:
                            _port_pid_ctrl.kp = _scaled_value
                        _stbd_pid_ctrl.kp = _scaled_value

                        _value = _rotary_ctrl.read()
#                       _log.info(Fore.BLUE + Style.BRIGHT + 'rotary value: {:<5.2f}'.format(_value))
                    
                    #   if _value > -2.0 and _value < 2.0: # hysteresis?
                    #       _value = 0.0
                        
                        if ORIENTATION == Orientation.BOTH or ORIENTATION == Orientation.PORT:
                            _port_pid_ctrl.setpoint = ROTATE_VALUE * _value #* 100.0
                            _port_setpoint = _port_pid_ctrl.setpoint
                        if ORIENTATION == Orientation.BOTH or ORIENTATION == Orientation.STBD:
                            _stbd_pid_ctrl.setpoint = _value #* 100.0
                            _stbd_setpoint = _stbd_pid_ctrl.setpoint
                        
#                       _log.info(Fore.MAGENTA + 'rotary value: {:<5.2f}; setpoint: '.format(_value) \
#                               + Fore.RED + ' {:5.2f};'.format(_port_setpoint) + Fore.GREEN + ' {:5.2f};'.format(_stbd_setpoint) \
#                               + Fore.WHITE + ' action_B: {}'.format(action_B))
                        # end of loop

                    action_B = False # quit after action
                    time.sleep(1.0)
                    # and we now return to our regularly scheduled broadcast...

                else:
                    pass
                _log.info(Fore.BLACK + Style.BRIGHT + 'waiting on button A...')
                time.sleep(0.5)

            _log.info(Fore.YELLOW + 'end of test.')

        except KeyboardInterrupt:
            _log.info(Fore.CYAN + Style.BRIGHT + 'Ctrl-C caught: closing...')
        finally:
            if ORIENTATION == Orientation.BOTH or ORIENTATION == Orientation.PORT:
                _port_pid_ctrl.disable()
            if ORIENTATION == Orientation.BOTH or ORIENTATION == Orientation.STBD:
                _stbd_pid_ctrl.disable()
            _motors.brake()
            if _rotary_ctrl:
                _log.info('resetting rotary encoder...')
                _rotary_ctrl.reset()
            time.sleep(1.0)
            _log.info('complete.')

    except Exception as e:
        _log.info(Fore.RED + Style.BRIGHT + 'error in test: {}'.format(e, traceback.format_exc()))
    finally:
        _log.info(Fore.YELLOW + Style.BRIGHT + 'finally.')

if __name__== "__main__":
    main()

#EOF
