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
from lib.status import Status
from lib.enums import Speed, Color, Orientation
from lib.motors import Motors
from lib.logger import Logger, Level
from lib.lidar import Lidar
from lib.rgbmatrix import RgbMatrix, DisplayType

step_value = 5.0

class Controller():
    '''
        Responds to Events.
    '''
    def __init__(self, level, config, switch, infrared_trio, motors, rgbmatrix, lidar, callback_shutdown):
        super().__init__()
        self._log = Logger('controller', level)
        self._config = config
        self._enable_self_shutdown = self._config['ros'].get('enable_self_shutdown')
        self._switch = switch
#       self._info = info
        self._infrared_trio = infrared_trio
        self._motors = motors
        self._rgbmatrix = rgbmatrix
        self._lidar = lidar
        self._callback_shutdown = callback_shutdown
        self._status = Status(GPIO, level)
        self._current_message = None
        self._standby = False
        self._log.debug('ready.')


    # ..........................................................................
    def set_standby(self, is_standby):
        if is_standby:
            self._status.blink(True)
            self._motors.disable()
            self._switch.off()
            self._infrared_trio.disable()
            self._standby = True
        else:
            self._status.blink(False)
            self._motors.enable()
            self._switch.on()
            self._infrared_trio.enable()
            self._status.enable()
            self._standby = False


    # ..........................................................................
    def get_current_message(self):
        return self._current_message


    # ..........................................................................
    def _clear_current_message(self):
        self._current_message = None
        self._log.info('clear current message  {}.'.format(self._current_message))


    # ..........................................................................
    def act(self, message, callback):
        '''
            Responds to the Event contained within the Message.
        '''
        self._current_message = message
        _port_speed = self._motors.get_current_power_level(Orientation.PORT)
        _stbd_speed = self._motors.get_current_power_level(Orientation.STBD)
        if _port_speed is not None and _stbd_speed is not None:
            self._log.debug('last set power port: {:6.1f}, starboard: {:6.1f}'.format(_port_speed, _stbd_speed))
        else:
            self._log.debug('last set power port: {}, starboard: {}'.format(_port_speed, _stbd_speed))

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
        if self._standby:
            self._log.info('event: disabled, currently in standby mode.')
            callback(self._current_message, self._motors.get_current_power_levels())


        # ballistic behaviours ...........................................................

        # BATTERY_LOW             ..............................................
        elif event is Event.BATTERY_LOW:
            if self._enable_self_shutdown:
                self._log.critical('event: battery low.')
                self.set_standby(True)
                self._current_message.complete()
                self._callback_shutdown()
            else:
                self._log.warning('event ignored: battery low (self shutdown disabled).')
                self._current_message.complete()
#               callback(self._current_message, None)
#               self._clear_current_message()
#               return


        # SHUTDOWN                ..............................................
        # shutdown .............................................................
        elif event is Event.SHUTDOWN:
            if self._enable_self_shutdown:
                self._log.info('event: shutdown.')
                self.set_standby(True)
                self._callback_shutdown()
            else:
                self._log.warning('event ignored: shutdown (self shutdown disabled).')
#               self._current_message.complete()
#               callback(self._current_message, None)
#               self._clear_current_message()
#               return


        #     # stopping and halting ...................................................

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
                self._infrared_trio.disable()
                self._motors.stop()
#               self._info.blink_side(Orientation.PORT, 1)
#               self._motors.astern(Speed.HALF.value)
                self._motors.turnAstern(Speed.THREE_QUARTER.value, Speed.HALF.value)
                time.sleep(0.5)
                self._motors.brake()
                self._infrared_trio.enable()
                self._log.info('action complete: port bumper.')
            else:
                self._log.info('no action required (not moving): port bumper.')


        # BUMPER_CENTER           ..............................................
        elif event is Event.BUMPER_CENTER:
            self._log.info(Style.BRIGHT + 'event:' + Style.NORMAL + Fore.BLUE + ' center bumper.' + Style.RESET_ALL)
            if self._motors.is_in_motion(): # if we're moving then halt
                self._infrared_trio.disable()
                self._motors.stop()
#               self._info.blink(1)
                self._motors.astern(Speed.HALF.value)
                time.sleep(0.5)
                self._motors.brake()
                self._infrared_trio.enable()
                self._log.info('action complete: center bumper.')
            else:
                self._log.info('no action required (not moving): center bumper.')


        # BUMPER_STBD        ..............................................
        elif event is Event.BUMPER_STBD:
            self._log.info(Style.BRIGHT + 'event:' + Style.NORMAL + Fore.GREEN + ' starboard bumper.' + Style.RESET_ALL)
            if self._motors.is_in_motion(): # if we're moving then halt
                self._motors.stop()
#               self._info.blink_side(Orientation.STBD, 1)
#               self._motors.astern(Speed.FULL.value)
                self._motors.turnAstern(Speed.HALF.value, Speed.THREE_QUARTER.value)
                time.sleep(0.5)
                self._motors.brake()
                self._log.info('action complete: starboard bumper.')
            else:
                self._log.info('no action required (not moving): starboard bumper.')


        # BUMPER_UPPER            ..............................................
        elif event is Event.BUMPER_UPPER:
            self._log.info(Fore.RED + Style.BRIGHT + 'event: emergency stop.')
            self._motors.stop()


        # # infrared ...........................................................
        # INFRARED_PORT           ..............................................
        elif event is Event.INFRARED_PORT:
            self._log.info(Style.BRIGHT + 'event:' + Style.NORMAL + Fore.RED + ' port infrared.' + Style.RESET_ALL)
            if self._motors.is_in_motion(): # if we're moving then halt
                self._infrared_trio.disable()
                self._motors.halt()
#               self._info.blink_side(Orientation.PORT, 1)
#               self._motors.astern(Speed.HALF.value)
                self._motors.turnAstern(Speed.THREE_QUARTER.value, Speed.HALF.value)
                time.sleep(0.1)
                self._motors.brake()
                self._infrared_trio.enable()
                self._log.info('action complete: port infrared.')
            else:
                self._log.info('no action required (not moving): port infrared.')


        # INFRARED_CENTER         ..............................................
        elif event is Event.INFRARED_CENTER:
            self._log.info(Style.BRIGHT + 'event:' + Style.NORMAL + Fore.BLUE + ' center infrared.' + Style.RESET_ALL)
            if self._motors.is_in_motion(): # if we're moving then halt
                self._infrared_trio.disable()
                self._motors.halt()
#               self._info.blink(1)
                self._motors.astern(Speed.HALF.value)
                time.sleep(0.2)
                self._motors.brake()
                self._infrared_trio.enable()
                self._log.info('action complete: center infrared.')
            else:
                self._log.info('no action required (not moving): center infrared.')


        # INFRARED_SHORT_RANGE         .........................................
        elif event is Event.INFRARED_SHORT_RANGE:
            self._log.info(Style.BRIGHT + 'event:' + Style.NORMAL + Fore.BLUE + ' short range infrared.' + Style.RESET_ALL)
            if self._motors.is_in_motion(): # if we're moving then halt
                self._infrared_trio.disable()
                self._motors.halt()
#               self._info.blink(1)
                self._motors.astern(Speed.HALF.value)
                time.sleep(0.34)
                self._motors.brake()
                self._infrared_trio.enable()
                self._log.info('action complete: short range infrared.')
            else:
                self._log.info('no action required (not moving): short range infrared.')
            self._infrared_trio.set_long_range_scan(True)


        # INFRARED_LONG_RANGE         .........................................
        elif event is Event.INFRARED_LONG_RANGE:
            self._log.info(Style.BRIGHT + 'event:' + Style.NORMAL + Fore.BLUE + ' long range infrared.' + Style.RESET_ALL)
            if self._motors.is_in_motion(): # if we're moving then halt
                self._log.critical("WE'RE GOING TOO FAST!         xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx ")
                self._infrared_trio.set_long_range_scan(False)
                self._motors.change_speed(Speed.DEAD_SLOW.value)
#               self._motors.ahead(Speed.DEAD_SLOW.value)
                self._log.info('action complete: long range infrared.')
#           if self._motors.is_faster_than(Speed.SLOW) or True: # if we're moving fast then slow down
#               self._log.critical('WE\'RE GOING TOO FAST!')
#               self._motors.ahead(Speed.SLOW.value)
#               self._log.info('action complete: long range infrared.')
            else:
                self._log.critical('no action required (not moving): long range infrared.')


        # INFRARED_STBD      ..............................................
        elif event is Event.INFRARED_STBD:
            self._log.info(Style.BRIGHT + 'event:' + Style.NORMAL + Fore.GREEN + ' starboard infrared.' + Style.RESET_ALL)
            if self._motors.is_in_motion(): # if we're moving then halt
                self._motors.halt()
#               self._info.blink_side(Orientation.STBD, 1)
#               self._motors.astern(Speed.FULL.value)
                self._motors.turnAstern(Speed.HALF.value, Speed.THREE_QUARTER.value)
                time.sleep(0.1)
                self._motors.brake()
                self._log.info('action complete: starboard infrared.')
            else:
                self._log.info('no action required (not moving): starboard infrared.')


        # # emergency movements ................................................
        # EMERGENCY_ASTERN        ..............................................

        # # movement ahead .....................................................
        # FULL_AHEAD              ..............................................
        # HALF_AHEAD              ..............................................
        # SLOW_AHEAD              ..............................................
        # DEAD_SLOW_AHEAD         ..............................................

        # AHEAD                   ..............................................
        # 8 ahead ..............................................................
        elif event is Event.AHEAD:
            if self._infrared_trio.get_long_range_hits() > 0:
                self._log.info('event: ahead slow speed.')
                _port_speed = Speed.SLOW.value
                _stbd_speed = Speed.SLOW.value
            else:
                self._log.info('event: ahead half speed.')
                _port_speed = Speed.HALF.value
                _stbd_speed = Speed.HALF.value
            self._motors.ahead(Speed.HALF.value)
            self._log.info('action complete: ahead.')


        # # movement astern ....................................................
        # ASTERN                  ..............................................
        # 2 astern .............................................................
        elif event is Event.ASTERN:
#           _port_speed = -1.0 * Speed.HALF.value
#           _stbd_speed = -1.0 * Speed.HALF.value
            self._log.critical('event: astern.')
            self._infrared_trio.disable()
            self._motors.astern(Speed.HALF.value)
            self._infrared_trio.enable()
            self._log.critical('event (returned already): astern.')

        # DEAD_SLOW_ASTERN        ..............................................
        # SLOW_ASTERN             ..............................................
        # HALF_ASTERN             ..............................................
        # FULL_ASTERN             ..............................................

        # # relative change ....................................................
        # INCREASE_SPEED          ..............................................
        # EVEN                    ..............................................
        # DECREASE_SPEED          ..............................................

        # # port turns .........................................................
        # TURN_AHEAD_PORT         ..............................................
        # 9 turn ahead port ....................................................
        elif event is Event.TURN_AHEAD_PORT:
            self._log.critical('event: turn ahead to port.')
            _stbd_speed += step_value
            _stbd_speed = min(Speed.MAXIMUM.value, _stbd_speed)
            self._log.info('event: turn ahead to port: {:6.1f}, {:6.1f}'.format(_port_speed, _stbd_speed))
            self._motors.turnAhead(_port_speed, _stbd_speed)

        # TURN_TO_PORT            ..............................................
        # TURN_ASTERN_PORT        ..............................................

        # SPIN_PORT               ..............................................
        # 4 spin counter-clockwise .............................................
        elif event is Event.SPIN_PORT:
            self._log.info('event: spinPort.')
            self._motors.spinPort(Speed.THREE_QUARTER.value)


        # # starboard turns ....................................................

        # SPIN_STBD          ..............................................
        # 6 spin clockwise .....................................................
        elif event is Event.SPIN_STBD:
            self._log.info('event: spinStarboard.')
            self._motors.spinStarboard(Speed.THREE_QUARTER.value)

        # TURN_ASTERN_STBD   ..............................................
        # TURN_TO_STBD       ..............................................

        # TURN_AHEAD_STBD    ..............................................
        # 7 turn ahead starboard ...............................................
        elif event is Event.TURN_AHEAD_STBD:
            self._log.critical('event: turn ahead to starboard.')
            _port_speed += step_value
            _port_speed = min(Speed.MAXIMUM.value, _port_speed)
            self._log.info('Turn ahead to starboard: {:6.1f}, {:6.1f}'.format(_port_speed, _stbd_speed))
            self._motors.turnAhead(_port_speed, _stbd_speed)

        # ROAM                    ..............................................
        elif event is Event.ROAM:
            self._log.critical('event: roam.')
            self._lidar.enable()
            self._rgbmatrix.disable()
            self._rgbmatrix.clear()
            values = self._lidar.scan()

#           time.sleep(2.0)
#           self._infrared_trio.disable()
#           self._motors.spinPort(Speed.THREE_QUARTER.value)
#           time.sleep(0.20)
#           self._motors.halt()
#           self._motors.ahead(Speed.HALF.value)
#           self._infrared_trio.enable()
#           time.sleep(2.3)
#           self._motors.spinStarboard(Speed.THREE_QUARTER.value)
#           time.sleep(0.4)
#           self._motors.ahead(Speed.HALF.value)
#           time.sleep(1.4)
#           self._motors.halt()

#           self._motors.spinPort(Speed.THREE_QUARTER.value)
#           time.sleep(2.0)
#           self._motors.halt()
#           for i in range(5):
#               self._rgbmatrix.set_color(Color.GREEN)
#               time.sleep(0.5)
#               self._rgbmatrix.set_color(Color.BLACK)
#               time.sleep(0.5)
#           self._rgbmatrix.set_color(Color.BLACK)

            self._log.critical('scan complete.')


        # non-ballistic behaviours .......................................................

        else:
            self._log.error('unrecognised event: {}'.format(event))
            pass

        callback(self._current_message, self._motors.get_current_power_levels())
        self._clear_current_message()


#EOF
