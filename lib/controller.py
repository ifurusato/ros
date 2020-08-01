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
from flask import jsonify
from colorama import init, Fore, Style
init()

from lib.import_gpio import *
from lib.event import Event
#from lib.status import Status
from lib.enums import Speed, Color, Orientation
from lib.motors import Motors
from lib.logger import Logger, Level

step_value = 5.0

class Controller():
    '''
        Responds to Events.
    '''
#   def __init__(self, level, config, switch, infrared_trio, motors, rgbmatrix, lidar, callback_shutdown):
    def __init__(self, config, switch, ifs, motors, callback_shutdown, level):
        super().__init__()
        self._log = Logger('controller', level)
        self._config = config
        self._enable_self_shutdown = self._config['ros'].get('enable_self_shutdown')
        self._switch = switch
        self._ifs = ifs
        self._motors = motors
        self._callback_shutdown = callback_shutdown
#       self._status = Status(config, GPIO, level)
        self._current_message = None
        self._standby = False
        self._log.debug('ready.')


    # ..........................................................................
    def set_standby(self, is_standby):
        if is_standby:
            self._log.info('standby.')
#           self._status.blink(True)
            self._motors.disable()
            self._switch.off()
            self._ifs.disable()
            self._standby = True
        else:
            self._log.info('active.')
#           self._status.blink(False)
            self._motors.enable()
            self._switch.on()
            self._ifs.enable()
#           self._status.enable()
            self._standby = False


    # ..........................................................................
    def get_current_message(self):
        return self._current_message


    # ..........................................................................
    def _clear_current_message(self):
        self._log.debug('clear current message  {}.'.format(self._current_message))
        self._current_message = None


    # ..........................................................................
    def act(self, message, callback):
        '''
            Responds to the Event contained within the Message.
        '''
        self._current_message = message
#       _port_speed = self._motors.get_current_power_level(Orientation.PORT)
#       _stbd_speed = self._motors.get_current_power_level(Orientation.STBD)
#       if _port_speed is not None and _stbd_speed is not None:
#           self._log.debug('last set power port: {:6.1f}, starboard: {:6.1f}'.format(_port_speed, _stbd_speed))
#       else:
#           self._log.debug('last set power port: {}, starboard: {}'.format(_port_speed, _stbd_speed))

        event = self._current_message.get_event()
        self._current_message.start()

        # BUTTON                  ..............................................
        # button ...............................................................
        if event is Event.BUTTON:
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
#           if self._standby:


#       # stopping and halting ...................................................

        # STOP                    ..............................................
        # stop .................................................................
        elif event is Event.STOP:
            self._log.info('event: stop.')
            self._motors.stop()
    
        # HALT                    ..............................................
        # halt .................................................................
        elif event is Event.HALT:
            self._log.info('event: halt.')
            self._motors.halt()

        # BRAKE                   ...................................
        # brake ................................................................
        elif event is Event.BRAKE:
            self._log.info('event: brake.')
            self._motors.brake()

        # STANDBY                 ..............................................
        # standby ..............................................................
        elif event is Event.STANDBY:
            self._log.info('event: standby.')
            # disable motors until button press
            self._motors.disable()
            self._switch.off()
            self._standby = True


        # # bumper .............................................................
        # BUMPER_PORT             ..............................................
        elif event is Event.BUMPER_PORT:
            self._log.info(Style.BRIGHT + 'event:' + Style.NORMAL + Fore.RED + ' port bumper.' + Style.RESET_ALL)
            if self._motors.is_in_motion(): # if we're moving then halt
                self._ifs.disable()
                self._motors.stop()
#               self._motors.astern(Speed.HALF.value)
                self._motors.turnAstern(Speed.THREE_QUARTER.value, Speed.HALF.value)
                time.sleep(0.5)
                self._motors.brake()
                self._ifs.enable()
                self._log.info('action complete: port bumper.')
            else:
                self._log.info('no action required (not moving): port bumper.')


        # BUMPER_CENTER           ..............................................
        elif event is Event.BUMPER_CENTER:
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
        elif event is Event.BUMPER_STBD:
            self._log.info(Style.BRIGHT + 'event:' + Style.NORMAL + Fore.GREEN + ' starboard bumper.' + Style.RESET_ALL)
            if self._motors.is_in_motion(): # if we're moving then halt
                self._motors.stop()
#               self._motors.astern(Speed.FULL.value)
                self._motors.turnAstern(Speed.HALF.value, Speed.THREE_QUARTER.value)
                time.sleep(0.5)
                self._motors.brake()
                self._log.info('action complete: starboard bumper.')
            else:
                self._log.info('no action required (not moving): starboard bumper.')


        # # infrared ...........................................................

        # INFRARED_PORT_SIDE      ..............................................
        elif event is Event.INFRARED_PORT_SIDE:
            _value = message.get_value()
            self._log.info(Style.BRIGHT + 'event:' + Style.NORMAL + Fore.RED + ' port side infrared' + Fore.YELLOW + '; value: {}'.format(_value) )
            pass


        # INFRARED_PORT           ..............................................
        elif event is Event.INFRARED_PORT:
            _value = message.get_value()
            self._log.info(Style.BRIGHT + 'event:' + Style.NORMAL + Fore.RED + ' port infrared' + Fore.YELLOW + '; value: {}'.format(_value) )
            if self._motors.is_in_motion(): # if we're moving then halt
                self._ifs.disable()
                self._motors.halt()
#               self._motors.astern(Speed.HALF.value)
                self._motors.turnAstern(Speed.THREE_QUARTER.value, Speed.HALF.value)
                time.sleep(0.1)
                self._motors.brake()
                self._ifs.enable()
                self._log.info('action complete: port infrared.')
            else:
                self._log.info('no action required (not moving): port infrared.')


        # INFRARED_CENTER         ..............................................
        elif event is Event.INFRARED_CENTER:
            _value = message.get_value()
            self._log.info(Style.BRIGHT + 'event:' + Style.NORMAL + Fore.BLUE + ' center infrared' + Fore.YELLOW + '; value: {}'.format(_value) )
            if self._motors.is_in_motion(): # if we're moving then halt
                self._ifs.disable()
                self._motors.halt()
                self._motors.astern(Speed.HALF.value)
                time.sleep(0.2)
                self._motors.brake()
                self._ifs.enable()
                self._log.info('action complete: center infrared.')
            else:
                self._log.info('no action required (not moving): center infrared.')


        # INFRARED_STBD      ...................................................
        elif event is Event.INFRARED_STBD:
            _value = message.get_value()
            self._log.info(Style.BRIGHT + 'event:' + Style.NORMAL + Fore.GREEN + ' starboard infrared' + Fore.YELLOW + '; value: {}'.format(_value) )
            if self._motors.is_in_motion(): # if we're moving then halt
                self._motors.halt()
#               self._motors.astern(Speed.FULL.value)
                self._motors.turnAstern(Speed.HALF.value, Speed.THREE_QUARTER.value)
                time.sleep(0.1)
                self._motors.brake()
                self._log.info('action complete: starboard infrared.')
            else:
                self._log.info('no action required (not moving): starboard infrared.')


        # INFRARED_STBD_SIDE         ...........................................
        elif event is Event.INFRARED_STBD_SIDE:
            _value = message.get_value()
            self._log.info(Style.BRIGHT + 'event:' + Style.NORMAL + Fore.GREEN + ' starboard side infrared' + Fore.YELLOW + '; value: {}'.format(_value) )
            pass


        # EVENT UNKNOWN: FAILURE ...............................................
        else:
            self._log.error('unrecognised event: {}'.format(event))
            pass

        _current_power_levels = self._motors.get_current_power_levels()
        self._log.info(Fore.MAGENTA + 'callback message: {}; '.format(self._current_message.get_value()) + Fore.CYAN + 'current power levels: {}'.format( _current_power_levels))
        callback(self._current_message, _current_power_levels)
        self._clear_current_message()


#EOF
