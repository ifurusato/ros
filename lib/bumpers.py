#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# Copyright 2020 by Murray Altheim. All rights reserved. This file is part of
# the Robot OS project and is released under the "Apache Licence, Version 2.0".
# Please see the LICENSE file included as part of this package.
#

from colorama import init, Fore, Style
init()

from lib.devnull import DevNull
from lib.logger import Level, Logger
from lib.event import Event
from lib.message import Message
from lib.bumper import Bumper

# ..............................................................................
class Bumpers():

    def __init__(self, config, queue, upper_activated_callback, level):
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
        if self._config is None:
            raise ValueError("no configuration provided.")
        self._config = config
        _config = self._config['ros'].get('bumper')
        self._port_pin  = _config.get('port_pin')
        self._cntr_pin  = _config.get('center_pin')
        self._stbd_pin  = _config.get('starboard_pin')
        self._upper_pin = _config.get('upper_pin')
        self._log.info('bumper pins: port={:d}; center={:d}; starboard={:d}; upper={:d}'.format(\
                self._port_pin, self._cntr_pin, self._stbd_pin, self._upper_pin)) 
        self._queue = queue

        # these auto-start their threads
        self._bumper_port   = Bumper(self._port_pin, 'port', level, self.activated_port, self.deactivated_port )
        self._bumper_center = Bumper(self._cntr_pin, 'cntr', level, self.activated_center, self.deactivated_center )
        self._bumper_stbd   = Bumper(self._stbd_pin, 'stbd', level, self.activated_stbd, self.deactivated_stbd )

        if upper_activated_callback is not None:
            self._bumper_upper = Bumper(self._upper_pin, 'uppr', level, upper_activated_callback, self.deactivated_upper )
        else:
            self._bumper_upper = Bumper(self._upper_pin, 'uppr', level, self.activated_upper, self.deactivated_upper )
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
            self._queue.add(Message(Event.BUMPER_CNTR))
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
