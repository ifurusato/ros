#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# Copyright 2020 by Murray Altheim. All rights reserved. This file is part of
# the Robot OS project and is released under the "Apache Licence, Version 2.0".
# Please see the LICENSE file included as part of this package.
#

from colorama import init, Fore, Style
init()

from .devnull import DevNull
from .logger import Level, Logger
from .event import Event
from .message import Message
from .bumper import Bumper

# ..............................................................................
class Bumpers():

    def __init__(self, queue, upper_activated_callback, level):
        '''
        This uses the hardcoded pin numbers found in the class, supporting four
        bumpers: port, center, starboard, and upper (emergency stop) wire feelers.

        Parameters:

           queue:  the message queue to receive messages from this task
           upper_activated_callback: the optional callback used on the upper feelers
           level:  the logging level
        '''
        super().__init__()
        self._log = Logger('bumpers', level)
        self._log.debug('initialising bumpers...')
        self._queue = queue

        PORT_PIN   = 13
        CENTER_PIN = 19
#       STBD_PIN   = 26
        STBD_PIN   =  7
        UPPER_PIN  = 15

        # these auto-start their threads
        self._bumper_port   = Bumper(PORT_PIN,     'port', level, self.activated_port, self.deactivated_port )
        self._bumper_center = Bumper(CENTER_PIN,   'cntr', level, self.activated_center, self.deactivated_center )
        self._bumper_stbd   = Bumper(STBD_PIN,     'stbd', level, self.activated_stbd, self.deactivated_stbd )

        if upper_activated_callback is not None:
            self._bumper_upper = Bumper(UPPER_PIN, 'uppr', level, upper_activated_callback, self.deactivated_upper )
        else:
            self._bumper_upper = Bumper(UPPER_PIN, 'uppr', level, self.activated_upper, self.deactivated_upper )
        self._bumper_upper.set_wait_for_inactive(False) # no delay on deactivation
        self._enabled = False
        self._log.info('ready.')


    def activated_port(self):
        if self._enabled:
            self._log.info(Style.BRIGHT + 'activated: ' + Style.NORMAL + Fore.RED + 'port bumper sensor.' + Style.RESET_ALL)
            self._queue.add(Message(Event.BUMPER_PORT))
        else:
            self._log.info('[DISABLED] bumper activated port.')
        pass

    def deactivated_port(self):
        if self._enabled:
            self._log.debug(Style.DIM + 'deactivated: ' + Style.NORMAL + Fore.RED + 'port bumper sensor.' + Style.RESET_ALL)
        else:
            self._log.debug('[DISABLED] bumper deactivated port.')
        pass

    def activated_center(self):
        if self._enabled:
            self._log.info(Style.BRIGHT + 'activated: ' + Style.NORMAL + Fore.BLUE + 'center bumper sensor.' + Style.RESET_ALL)
            self._queue.add(Message(Event.BUMPER_CENTER))
        else:
            self._log.info('[DISABLED] bumper activated center.')
        pass

    def deactivated_center(self):
        if self._enabled:
            self._log.debug(Style.DIM + 'deactivated: ' + Style.NORMAL + Fore.BLUE + 'center bumper sensor.' + Style.RESET_ALL)
        else:
            self._log.debug('[DISABLED] bumper deactivated center.')
        pass

    def activated_stbd(self):
        if self._enabled:
            self._log.info(Style.BRIGHT + 'activated: ' + Style.NORMAL + Fore.GREEN + 'starboard bumper sensor.' + Style.RESET_ALL)
            self._queue.add(Message(Event.BUMPER_STBD))
        else:
            self._log.info('[DISABLED] bumper activated starboard.')
        pass

    def deactivated_stbd(self):
        if self._enabled:
            self._log.debug(Style.DIM + 'deactivated: ' + Style.NORMAL + Fore.GREEN + 'starboard bumper sensor.' + Style.RESET_ALL)
        else:
            self._log.debug('[DISABLED] bumper deactivated starboard.')
        pass

    def activated_upper(self):
        if self._enabled:
            self._log.info(Style.BRIGHT + 'activated: ' + Style.NORMAL + Fore.YELLOW + 'upper bumper sensor.' + Style.RESET_ALL)
            self._queue.add(Message(Event.BUMPER_UPPER))
        else:
            self._log.info('[DISABLED] bumper activated upper.')
        pass

    def deactivated_upper(self):
        if self._enabled:
            self._log.debug(Style.DIM + 'deactivated: ' + Style.NORMAL + Fore.YELLOW + 'upper bumper sensor.' + Style.RESET_ALL)
        else:
            self._log.debug('[DISABLED] bumper deactivated upper.')
        pass


    # ..........................................................................
    def enable(self):
        self._log.info('bumpers enabled.')
        self._bumper_port.enable()
        self._bumper_center.enable()
        self._bumper_stbd.enable()
        self._bumper_upper.enable()
        self._enabled = True


    # ..........................................................................
    def disable(self):
        self._log.info('bumpers disabled.')
        self._bumper_port.disable()
        self._bumper_center.disable()
        self._bumper_stbd.disable()
        self._bumper_upper.disable()
        self._enabled = False


    # ......................................................
    def close(self):
        self._log.info('bumpers closed.')
        self._enabled = False
        self._bumper_port.close()
        self._bumper_center.close()
        self._bumper_stbd.close()
        self._bumper_upper.close()


#EOF
