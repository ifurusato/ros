#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# Copyright 2020 by Murray Altheim. All rights reserved. This file is part
# of the pimaster2ardslave project and is released under the MIT Licence;
# please see the LICENSE file included as part of this package.
#
# author:   Murray Altheim
# created:  2020-04-30
# modified: 2020-05-24
#
#  This just displays messages from the Integrated Front Sensor to sysout.
#

import itertools, sys, threading, time, traceback
from colorama import init, Fore, Style
init()

from lib.logger import Logger, Level
from lib.config_loader import ConfigLoader
from lib.event import Event
from lib.message import Message
from lib.message_factory import MessageFactory
from lib.message_bus import MessageBus
from lib.queue import MessageQueue
from lib.clock import Clock
from lib.ifs import IntegratedFrontSensor
#rom lib.indicator import Indicator
from lib.rate import Rate
from lib.slew import SlewRate
from lib.motors import Motors
from lib.pid_motor_ctrl import PIDMotorController

# ..............................................................................
class MotorController():

    def __init__(self, motor_controller, level):
        super().__init__()
        self._log = Logger("mc", level)
        self._motors = motor_controller.get_motors()
        _controllers = motor_controller.get_pid_controllers()
        self._port_pid = _controllers[0]
        self._stbd_pid = _controllers[1]
        self._cruising_velocity = 0.0
        self._enabled = False
        self._log.info('ready.')

    # ..........................................................................
    def set_cruising_velocity(self, value):
        self._cruising_velocity = value

    # ..........................................................................
    def disable(self):
        self._enabled = False

    # ..........................................................................
    def cruise(self):
        self._log.info('start cruising...')
        self._enabled = True
        _tp = threading.Thread(target=MotorController._cruise, args=[self, self._port_pid, self._cruising_velocity, lambda: self._enabled ])
        _ts = threading.Thread(target=MotorController._cruise, args=[self, self._stbd_pid, self._cruising_velocity, lambda: self._enabled ])
        self._log.info('cruise threads started.')
        _tp.start()
        _ts.start()
        self._log.info('cruise threads joining...')
        _tp.join()
        _ts.join()
        self._log.info('cruise complete.')

    # ..........................................................................
    def _cruise(self, pid, cruising_velocity, f_is_enabled):
        '''
           Threaded method for roaming.
        '''
        _rate = Rate(20)
        if not pid.enabled:       
            pid.enable()
        pid.set_slew_rate(SlewRate.NORMAL)
        pid.enable_slew(True)

        self._cruising_velocity = cruising_velocity

        self._log.info(Fore.YELLOW + '{} motor accelerating to velocity: {:5.2f}...'.format(pid.orientation.label, self._cruising_velocity))
        pid.velocity = self._cruising_velocity
        while pid.velocity < self._cruising_velocity:
            pid.velocity += 5.0
            self._log.info(Fore.GREEN + 'accelerating from {} to {}...'.format(pid.velocity, self._cruising_velocity ))
            time.sleep(0.5)
#           _rate.wait()

        self._log.info(Fore.YELLOW + '{} motor cruising...'.format(pid.orientation.label))
        while f_is_enabled:
            self._log.info(Fore.BLACK + '{} motor cruising at velocity: {:5.2f}...'.format(pid.orientation.label, pid.velocity))
            time.sleep(0.5)

        self._log.info(Fore.YELLOW + '{} motor decelerating...'.format(pid.orientation.label))
        pid.velocity = 0.0
        while pid.velocity > 0.0:
            pid.velocity -= 5.0
            self._log.info(Fore.GREEN + 'decelerating from {} to {}...'.format(pid.velocity, self._cruising_velocity ))
            time.sleep(0.01)
#           _rate.wait()

        self._log.info(Fore.YELLOW + '{} motor at rest.'.format(pid.orientation.label))
        time.sleep(1.0)
        pid.set_slew_rate(SlewRate.NORMAL)

        self._log.info(Fore.YELLOW + 'cruise complete.')

# ..............................................................................
class MockMessageQueue():
    '''
        This message queue just displays IFS events as they arrive.
    '''
    def __init__(self, level):
        super().__init__()
        self._counter = itertools.count()
        self._log = Logger("queue", Level.INFO)
        self._listeners = []
        self._log.info('ready.')

    # ..........................................................................
    def add_listener(self, listener):
        '''
        Add a listener to the optional list of message listeners.
        '''
        return self._listeners.append(listener)

    # ..........................................................................
    def remove_listener(self, listener):
        '''
        Remove the listener from the list of message listeners.
        '''
        try:
            self._listeners.remove(listener)
        except ValueError:
            self._log.warn('message listener was not in list.')

    # ......................................................
    def add(self, message):
        message.set_number(next(self._counter))
        self._log.debug('added message #{}: priority {}: {}'.format(message.get_number(), message.get_priority(), message.get_description()))
        _event = message.get_event()
        _value = message.value

        if _event is Event.INFRARED_PORT_SIDE:
            self._log.debug(Fore.RED + Style.BRIGHT + '> INFRARED_PORT_SIDE: {}; value: {}'.format(_event.description, _value))
        elif _event is Event.INFRARED_PORT_SIDE_FAR:
            self._log.debug(Fore.RED + Style.NORMAL + '> INFRARED_PORT_SIDE_FAR: {}; value: {}'.format(_event.description, _value))

        elif _event is Event.INFRARED_PORT:
            self._log.debug(Fore.MAGENTA + Style.BRIGHT + '> INFRARED_PORT: {}; value: {}'.format(_event.description, _value))
        elif _event is Event.INFRARED_PORT_FAR:
            self._log.debug(Fore.MAGENTA + Style.NORMAL + '> INFRARED_PORT_FAR: {}; value: {}'.format(_event.description, _value))
        # ..........................................................................................

        elif _event is Event.INFRARED_CNTR:
            self._log.info(Fore.BLUE + Style.BRIGHT + '> INFRARED_CNTR:     distance: {:>5.2f}cm'.format(_value))

        elif _event is Event.INFRARED_CNTR_FAR:
            self._log.info(Fore.BLUE + Style.NORMAL + '> INFRARED_CNTR_FAR: distance: {:5.2f}cm'.format(_value))

        # ..........................................................................................
        elif _event is Event.INFRARED_STBD:
            self._log.debug(Fore.CYAN + Style.BRIGHT + '> INFRARED_STBD: {}; value: {}'.format(_event.description, _value))
        elif _event is Event.INFRARED_STBD_FAR:
            self._log.debug(Fore.CYAN + Style.NORMAL + '> INFRARED_STBD_FAR: {}; value: {}'.format(_event.description, _value))

        elif _event is Event.INFRARED_STBD_SIDE:
            self._log.debug(Fore.GREEN + Style.BRIGHT + '> INFRARED_STBD_SIDE: {}; value: {}'.format(_event.description, _value))
        elif _event is Event.INFRARED_STBD_SIDE_FAR:
            self._log.debug(Fore.GREEN + Style.NORMAL + '> INFRARED_STBD_SIDE_FAR: {}; value: {}'.format(_event.description, _value))

        elif _event is Event.BUMPER_PORT:
            self._log.debug(Fore.RED + Style.BRIGHT + 'BUMPER_PORT: {}'.format(_event.description))
        elif _event is Event.BUMPER_CNTR:
            self._log.debug(Fore.BLUE + Style.BRIGHT + 'BUMPER_CNTR: {}'.format(_event.description))
        elif _event is Event.BUMPER_STBD:
            self._log.debug(Fore.GREEN + Style.BRIGHT + 'BUMPER_STBD: {}'.format(_event.description))
        else:
            self._log.debug(Fore.BLACK + Style.BRIGHT + 'other event: {}'.format(_event.description))

        # we're finished, now add to any listeners
        for listener in self._listeners:
            listener.add(message);

# ..............................................................................
def main():
    try:
        _log = Logger("test", Level.INFO)
        _log.info(Fore.BLUE + 'configuring...')

        # read YAML configuration
        _loader = ConfigLoader(Level.INFO)
        filename = 'config.yaml'
        _config = _loader.configure(filename)
        _queue = MockMessageQueue(Level.INFO)

        _motors = Motors(_config, None, Level.INFO)
        _pid_motor_ctrl = PIDMotorController(_config, _motors, Level.WARN)
        _motor_ctrl = MotorController(_pid_motor_ctrl, Level.INFO)
        _motor_ctrl.set_cruising_velocity(25.0)

        _message_factory = MessageFactory(Level.INFO)

        _message_bus = MessageBus(Level.INFO)
        _clock = Clock(_config, _message_bus, _message_factory, Level.INFO)

        _ifs = IntegratedFrontSensor(_config, _clock, _message_bus, _message_factory, Level.INFO)

        try:

            _log.info(Fore.BLUE + 'starting to cruise...')
            _motor_ctrl.cruise()
            time.sleep(2)

            _log.info(Fore.BLUE + 'cruising...')
            for i in range(5):
#           while True:
                _motor_ctrl.set_cruising_velocity(40.0)
                _log.info(Fore.BLUE + '{} cruising...'.format(i))
                time.sleep(1)

            _motor_ctrl.disable()

            _log.info(Fore.BLUE + 'exited loop.')
#           sys.exit(0)
#           _ifs.enable() 
#           while True:
#               time.sleep(1.0)

        except KeyboardInterrupt:
            print(Fore.RED + 'Ctrl-C caught; exiting...' + Style.RESET_ALL)

        _motor_ctrl.disable()
        _log.info(Fore.BLUE + 'post-try...')
        time.sleep(3)
        _pid_motor_ctrl.disable()
        _log.info(Fore.BLUE + 'exiting...')

    except Exception as e:
        print(Fore.RED + Style.BRIGHT + 'error: {}'.format(e))
        traceback.print_exc(file=sys.stdout)

if __name__== "__main__":
    main()

#EOF
