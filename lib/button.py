#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# Copyright 2020 by Murray Altheim. All rights reserved. This file is part of
# the Robot OS project and is released under the "Apache Licence, Version 2.0".
# Please see the LICENSE file included as part of this package.
#
# author:   Murray Altheim
# created:  2020-01-18
# modified: 2020-03-26
#

import time, threading
from colorama import init, Fore, Style
init()

from lib.abstract_task import AbstractTask
from lib.event import Event
from lib.message import Message

try:
    from gpiozero import Button as GpioButton
    print('import            :' + Fore.BLACK + ' INFO  : successfully imported gpiozero Button.' + Style.RESET_ALL)
except ImportError:
    print('import            :' + Fore.RED + ' ERROR : failed to import gpiozero Button, using mock...' + Style.RESET_ALL)
    from .mock_gpiozero import Button as GpioButton


ms = 50 / 1000 # 50ms loop delay

# ..............................................................................
class Button(AbstractTask):
    '''
        Button Task: reacts to pressing the red button.
        
        Usage:
    
           TOGGLE = False
           button = Button(TOGGLE, mutex)
           button.start()
           value = button.get()
    '''

    button_priority = 6

    def __init__(self, config, queue, mutex):
        '''
        Parameters:

           config:          the YAML-based application configuration
           queue:           the message queue to receive messages from this task
           mutex:           vs godzilla
        '''
        super().__init__("button", queue, None, Button.button_priority, mutex)
        if config is None:
            raise ValueError('no configuration provided.')
        self._queue = queue
        _config = config['ros'].get('button')
        _pin = _config.get('pin')
        self._toggle = _config.get('toggle') # if true, the value toggles when the button is pushed rather than acting as a momentary button
        self._log.info('initialising button on pin {:d}; toggle={}'.format(_pin, self._toggle))
        self._queue = queue
        self._button = GpioButton(_pin)
        self._value = False
        self._log.debug('ready.')


    # ......................................................
    def run(self):
        super(AbstractTask, self).run()
        self.enable()
        if self._toggle:
            self._button.when_released = self.toggle_state
        else:
            self.polling = threading.Thread(target=Button.poll, args=[self,])
            self.polling.start()


    # ......................................................
    def toggle_state(self):
        self._value = not self._value
        self._log.info("button toggle: {}".format(self._value))
        _message = Message(Event.BUTTON)
        _message.set_value(self._value)
        if self._queue:
            self._queue.add(_message)


    # ......................................................
    def poll(self):
        while self.is_enabled():
            if not self._toggle:
                self._value = self._button.is_pressed
                self._log.debug('button poll.')
            time.sleep(ms)


    # ..........................................................................
    def enable(self):
        super().enable()


    # ..........................................................................
    def disable(self):
        super().disable()


    # ......................................................
    def get(self):
        return self._value


    # ......................................................
    def close(self):
        super().close()


