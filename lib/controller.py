#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# Copyright 2020 by Murray Altheim. All rights reserved. This file is part of
# the Robot OS project and is released under the "Apache Licence, Version 2.0".
# Please see the LICENSE file included as part of this package.
#
# author:   Murray Altheim
# created:  2020-02-21
# modified: 2020-03-10

import time
import datetime as dt
from flask import jsonify
from colorama import init, Fore, Style
init()

from lib.import_gpio import *
from lib.event import Event
from lib.status import Status
from lib.enums import Speed, Direction, Velocity, SlewRate, Color, Orientation
from lib.motors import Motors
from lib.logger import Logger, Level
from lib.gamepad import Gamepad

# behaviours ....................
from lib.behaviours import Behaviours
from lib.roam import RoamBehaviour

step_value = 5.0

class Controller():
    '''
        Responds to Events. Simple tasks are handled within this script, more
        complicated ones are farmed out to task files.
    '''
#   def __init__(self, level, config, switch, infrared_trio, motors, rgbmatrix, lidar, callback_shutdown):
    def __init__(self, config, ifs, motors, callback_shutdown, level):
        super().__init__()
        self._log = Logger('controller', level)
        self._config = config
        self._enable_self_shutdown = self._config['ros'].get('enable_self_shutdown')
#       self._switch = switch
        self._ifs = ifs
        self._motors = motors
        self._port_motor = motors.get_motor(Orientation.PORT)
        self._port_pid = self._port_motor.get_pid_controller()
        self._stbd_motor = motors.get_motor(Orientation.STBD)
        self._stbd_pid = self._stbd_motor.get_pid_controller()
        self._callback_shutdown = callback_shutdown
        self._status = Status(config, GPIO, level)
        self._current_message = None
        self._standby = False
        self._enabled = True
        # behaviours .................................
        self._behaviours = Behaviours(motors, ifs, Level.INFO)
        self._roam_behaviour  = RoamBehaviour(motors, Level.INFO)
        self._log.debug('ready.')

    # ..........................................................................
    def set_standby(self, is_standby):
        if is_standby:
            self._log.info(Fore.RED + 'standby.')
            self._status.blink(True)
            self._motors.disable()
#           self._switch.off()
            self._ifs.disable()
            self._standby = True
        else:
            self._log.info(Fore.GREEN + 'active (standby off).')
            self._status.blink(False)
            self._motors.enable()
#           self._switch.on()
            self._ifs.enable()
            self._status.enable()
            self._standby = False

    # ................................................................
    def enable(self):
        self._enabled = True
        self._status.enable()
        self._log.info('enabled.')

    # ................................................................
    def disable(self):
        self._enabled = False
        self._status.disable()
        self._log.info('disabled.')

    # ..........................................................................
    def get_current_message(self):
        return self._current_message

    # ..........................................................................
    def _clear_current_message(self):
        self._log.debug('clear current message  {}.'.format(self._current_message))
        self._current_message = None

    # ..........................................................................
    def _slow_down(self, orientation):
        self._log.info(Fore.CYAN + 'slow down {}.'.format(orientation.name))
        self._motors.slow_down(orientation)
        pass

    # ..........................................................................
    def _avoid(self, orientation):
        self._log.info(Fore.CYAN + 'avoid {}.'.format(orientation.name))
        self._behaviours.avoid(orientation)

    # ..........................................................................
    def act(self, message, callback):
        '''
            Responds to the Event contained within the Message.
        '''
        if not self._enabled:
            self._log.warning('action ignored: controller disabled.')
            return

        _start_time = dt.datetime.now()
        self._current_message = message
#       _port_speed = self._motors.get_current_power_level(Orientation.PORT)
#       _stbd_speed = self._motors.get_current_power_level(Orientation.STBD)
#       if _port_speed is not None and _stbd_speed is not None:
#           self._log.debug('last set power port: {:6.1f}, starboard: {:6.1f}'.format(_port_speed, _stbd_speed))
#       else:
#           self._log.debug('last set power port: {}, starboard: {}'.format(_port_speed, _stbd_speed))

        _event = self._current_message.get_event()
        self._log.debug(Fore.CYAN + 'act()' + Style.BRIGHT + ' event: {}.'.format(_event) + Fore.YELLOW )
        self._current_message.start()

        # no action ............................................................
        if _event is Event.NO_ACTION:
            self._log.info('event: no action.')
            pass

        # BUTTON                  ..............................................
        # button ...............................................................
        elif _event is Event.BUTTON:
            # if button pressed we change standby mode but don't do anything else
            _value = self._current_message.get_value()
            # toggle value
#           self.set_standby(not _value) 
            if _value:
                self._log.critical('event: button value: {}.'.format(_value))
                self.set_standby(False)
            else:
                self._log.error('event: button value: {}.'.format(_value))
                self.set_standby(True)

            # if in standby mode we don't process the event, but we do perform the callback

#       # stopping and halting ...................................................

        # SHUTDOWN                ..............................................
        # shutdown ............................................................
        elif _event is Event.SHUTDOWN:
            self._log.info('event: shutdown.')
            self._motors.stop()
            self._callback_shutdown()
    
        # STOP                    ..............................................
        # stop .................................................................
        elif _event is Event.STOP:
            self._log.info('event: stop.')
            self._motors.stop()
    
        # HALT                    ..............................................
        # halt .................................................................
        elif _event is Event.HALT:
            self._log.info('event: halt.')
            self._motors.halt()

        # BRAKE                   ...................................
        # brake ................................................................
        elif _event is Event.BRAKE:
            self._log.info('event: brake.')
            self._motors.brake()

        # STANDBY                 ..............................................
        # standby ..............................................................
        elif _event is Event.STANDBY:
            # toggle standby state
            _value = self._current_message.get_value()
            if _value == 1:
                if self._standby:
                    self.set_standby(False)
                else:
                    self.set_standby(True)
            else:
                pass

        # ROAM                 .................................................
        elif _event is Event.ROAM:
            self._log.info('event: roam.')
            self._roam_behaviour.roam()

        # SNIFF                .................................................
        elif _event is Event.SNIFF:
            self._log.info('event: sniff.')
            self._behaviours.sniff()
            time.sleep(0.5) # debounce gamepad

        # D-PAD HORIZONTAL     .................................................
        elif _event is Event.FORWARD_VELOCITY:
            _direction = message.get_value()
            _speed = 80.0
            if _direction == -1: # then ahead
                self._log.info('event: d-pad movement: ahead.')
#               self._motors.change_velocity(0.5, 0.5, SlewRate.SLOW, -1)
                self._motors.ahead(_speed)
                time.sleep(2.0)
            elif _direction == 1: # then astern
                self._log.info('event: d-pad movement: astern.')
#               self._motors.change_velocity(-0.5, -0.5, SlewRate.SLOW, -1)
                self._motors.astern(_speed)
                time.sleep(2.0)
            else:
                self._log.info('event: d-pad movement: halt.')

        # D-PAD VERTICAL       .................................................
        elif _event is Event.THETA:
            _direction = message.get_value()
            if _direction == -1: # then ahead
                self._log.info('event: d-pad rotate: counter-clockwise.')
                self._motors.step(-100.0, 100.0, -1, -1)
                time.sleep(2.0)
            elif _direction == 1: # then astern
                self._log.info('event: d-pad rotate: clockwise.')
                self._motors.step(100.0, -100.0, -1, -1)
                time.sleep(2.0)
            else:
                self._log.info('event: d-pad rotate: none.')

        # PORT_VELOCITY         ................................................
        elif _event is Event.PORT_VELOCITY:
            _velocity = Gamepad.convert_range(message.get_value())
            self._log.info(Fore.GREEN + Style.BRIGHT + '{};\tvalue: {:>5.2f}'.format(_event.description, _velocity))
            self._port_motor.set_motor_power(_velocity)

        # PORT_THETA         ...................................................
        elif _event is Event.PORT_THETA:
            _velocity = -1 * Gamepad.convert_range(message.get_value())
            self._log.info(Fore.MAGENTA + Style.BRIGHT + '{};\tvalue: {:>5.2f}'.format(_event.description, _velocity))

        # STBD_VELOCITY         ................................................
        elif _event is Event.STBD_VELOCITY:
            _velocity = Gamepad.convert_range(message.get_value())
            self._log.info(Fore.GREEN + Style.BRIGHT + '{};\tvalue: {:>5.2f}'.format(_event.description, _velocity))
            self._stbd_motor.set_motor_power(_velocity)

        # STBD_THETA         ...................................................
        elif _event is Event.STBD_THETA:
            _velocity = -1 * Gamepad.convert_range(message.get_value())
            self._log.info(Fore.MAGENTA + Style.BRIGHT + '{};\tvalue: {:>5.2f}'.format(_event.description, _velocity))

        # # bumper .............................................................
        # BUMPER_PORT             ..............................................
        elif _event is Event.BUMPER_PORT:
            self._log.info(Style.BRIGHT + 'event:' + Style.NORMAL + Fore.RED + ' port bumper.' + Style.RESET_ALL)
            if self._motors.is_in_motion(): # if we're moving then halt
                self._ifs.disable()
                self._motors.stop()
#               self._motors.astern(Speed.HALF.value)
                self._motors.turn_astern(Speed.THREE_QUARTER.value, Speed.HALF.value)
                time.sleep(0.5)
                self._motors.brake()
                self._ifs.enable()
                self._log.info('action complete: port bumper.')
            else:
                self._log.info('no action required (not moving): port bumper.')

        # BUMPER_CNTR           ..............................................
        elif _event is Event.BUMPER_CNTR:
            self._log.info(Style.BRIGHT + 'event:' + Style.NORMAL + Fore.BLUE + ' center bumper.' + Style.RESET_ALL)
            if self._motors.is_in_motion(): # if we're moving then halt
                self._ifs.disable()
                self._motors.stop()
                self._motors.astern(Speed.HALF.value)
                time.sleep(0.5)
                self._motors.brake()
                self._ifs.enable()
                self._log.info('action complete: center bumper.')
            else:
                self._log.info('no action required (not moving): center bumper.')

        # BUMPER_STBD        ..............................................
        elif _event is Event.BUMPER_STBD:
            self._log.info(Style.BRIGHT + 'event:' + Style.NORMAL + Fore.GREEN + ' starboard bumper.' + Style.RESET_ALL)
            if self._motors.is_in_motion(): # if we're moving then halt
                self._motors.stop()
#               self._motors.astern(Speed.FULL.value)
                self._motors.turn_astern(Speed.HALF.value, Speed.THREE_QUARTER.value)
                time.sleep(0.5)
                self._motors.brake()
                self._log.info('action complete: starboard bumper.')
            else:
                self._log.info('no action required (not moving): starboard bumper.')

        # # infrared ...........................................................

        # INFRARED_PORT_SIDE      ..............................................
        elif _event is Event.INFRARED_PORT_SIDE:
            _value = message.get_value()
            self._log.info(Style.BRIGHT + 'event:' + Style.NORMAL + Fore.RED + ' port side infrared; ' + Fore.YELLOW + 'value: {}'.format(_value) )
            pass

        # INFRARED_PORT_SIDE_FAR      ..........................................
        elif _event is Event.INFRARED_PORT_SIDE_FAR:
            _value = message.get_value()
            self._log.info(Style.BRIGHT + 'event:' + Style.DIM + Fore.RED + ' port side infrared far; ' + Fore.YELLOW + 'value: {}'.format(_value) )
            pass

        # INFRARED_PORT           ..............................................
        elif _event is Event.INFRARED_PORT:
            _value = message.get_value()
            self._log.info(Style.BRIGHT + 'event:' + Style.NORMAL + Fore.RED + ' port infrared; ' + Fore.YELLOW + 'value: {}'.format(_value) )
            if self._motors.is_in_motion(): # if we're moving then avoid
                self._avoid(Orientation.PORT)
                self._log.info('action complete: port infrared.')
            else:
                self._log.info('no action required (not moving): port infrared.')
            pass

        # INFRARED_PORT_FAR           ..........................................
        elif _event is Event.INFRARED_PORT_FAR:
            _value = message.get_value()
            self._log.info(Style.BRIGHT + 'event:' + Style.DIM + Fore.RED + ' port infrared FAR; ' + Fore.YELLOW + 'value: {}'.format(_value) )
            if self._motors.is_in_motion(): # if we're moving then avoid
                self._slow_down(Orientation.PORT)
                self._log.info('action complete: port infrared far.')
            else:
                self._log.info('no action required (not moving): port infrared far.')
            pass

        # INFRARED_CNTR         ..............................................
        elif _event is Event.INFRARED_CNTR:
            _value = message.get_value()
            self._log.info(Style.BRIGHT + 'event:' + Style.NORMAL + Fore.BLUE + ' center infrared; ' + Fore.YELLOW + 'value: {}'.format(_value) )
            if self._motors.is_in_motion(): # if we're moving then avoid
                self._avoid(Orientation.CNTR)
                self._log.info('action complete: center infrared.')
            else:
                self._log.info('no action required (not moving): center infrared.')
            pass

        # INFRARED_CNTR_FAR         ..........................................
        elif _event is Event.INFRARED_CNTR_FAR:
            _value = message.get_value()
            self._log.info(Style.BRIGHT + 'event:' + Style.DIM + Fore.BLUE + ' center infrared FAR; ' + Fore.YELLOW + 'value: {}'.format(_value) )
            if self._motors.is_in_motion(): # if we're moving then avoid
                self._slow_down(Orientation.CNTR)
                self._log.info('action complete: center infrared far.')
            else:
                self._log.info('no action required (not moving): center infrared far.')
            pass

        # INFRARED_STBD      ...................................................
        elif _event is Event.INFRARED_STBD:
            _value = message.get_value()
            self._log.info(Style.BRIGHT + 'event:' + Style.NORMAL + Fore.GREEN + ' starboard infrared; ' + Fore.YELLOW + 'value: {}'.format(_value) )
            if self._motors.is_in_motion(): # if we're moving then avoid
                self._avoid(Orientation.STBD)
                self._log.info('action complete: starboard infrared.')
            else:
                self._log.info('no action required (not moving): starboard infrared.')
            pass

        # INFRARED_STBD_FAR      ...................................................
        elif _event is Event.INFRARED_STBD_FAR:
            _value = message.get_value()
            self._log.info(Style.BRIGHT + 'event:' + Style.DIM + Fore.GREEN + ' starboard infrared FAR; ' + Fore.YELLOW + 'value: {}'.format(_value) )
            if self._motors.is_in_motion(): # if we're moving then avoid
                self._slow_down(Orientation.STBD)
                self._log.info('action complete: starboard infrared far.')
            else:
                self._log.info('no action required (not moving): starboard infrared far.')
            pass

        # INFRARED_STBD_SIDE         ...........................................
        elif _event is Event.INFRARED_STBD_SIDE:
            _value = message.get_value()
            self._log.info(Style.BRIGHT + 'event:' + Style.NORMAL + Fore.GREEN + ' starboard side infrared; ' + Fore.YELLOW + 'value: {}'.format(_value) )
            pass

        # INFRARED_STBD_SIDE_FAR         .......................................
        elif _event is Event.INFRARED_STBD_SIDE_FAR:
            _value = message.get_value()
            self._log.info(Style.BRIGHT + 'event:' + Style.DIM + Fore.GREEN + ' starboard side infrared far; ' + Fore.YELLOW + 'value: {}'.format(_value) )
            pass

        # EVENT UNKNOWN: FAILURE ...............................................
        else:
            self._log.error('unrecognised event: {}'.format(_event))
            pass

        _current_power_levels = self._motors.get_current_power_levels()
        self._log.debug(Fore.MAGENTA + 'callback message: {}; '.format(self._current_message.get_value()) + Fore.CYAN + 'current power levels: {}'.format( _current_power_levels))
        callback(self._current_message, _current_power_levels)
        self._clear_current_message()

        _delta = dt.datetime.now() - _start_time
        _elapsed_ms = int(_delta.total_seconds() * 1000)
        self._log.info(Fore.MAGENTA + Style.DIM + 'elapsed: {}ms'.format(_elapsed_ms) + Style.DIM )

#EOF
