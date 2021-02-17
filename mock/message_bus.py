#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# Copyright 2020 by Murray Altheim. All rights reserved. This file is part of
# the Robot Operating System project and is released under the "Apache Licence,
# Version 2.0". Please see the LICENSE file included as part of this package.
#
# author:   Murray Altheim
# created:  2021-02-16
# modified: 2021-02-17
#

import itertools
from colorama import init, Fore, Style
init()

from lib.event import Event
from lib.message_factory import MessageFactory
from lib.message import Message
from lib.message_bus import MessageBus
from lib.logger import Logger, Level

# ..............................................................................
class MockMessageBus(MessageBus):
    '''
    This message bus just displays IFS events as they arrive.
    '''
    def __init__(self, level):
        super().__init__(level)
        self._count = 0
        self._counter = itertools.count()
#       self._log = Logger("message-bus", level)
        self._triggered_ir_port_side = self._triggered_ir_port  = self._triggered_ir_cntr  = self._triggered_ir_stbd  = \
        self._triggered_ir_stbd_side = self._triggered_bmp_port = self._triggered_bmp_cntr = self._triggered_bmp_stbd = 0
        self._limit = 3
        self._fmt = '{0:>9}'
        self._log.info('ready.')

    # ......................................................
    def _print_event(self, color, event, value):
        self._log.info('event:\t' + color + Style.BRIGHT + '{}; value: {}'.format(event.description, value))

    # ......................................................
    def handle(self, message: Message):
        self._count = next(self._counter)
        message.number = self._count
        _event = message.event
        self._log.info('handling message #{}; priority {}: {}; event: {}'.format(message.number, message.priority, message.description, _event))
        if _event is Event.BUMPER_PORT:
            self._print_event(Fore.RED, _event, message.value)
            if self._triggered_bmp_port < self._limit:
                self._triggered_bmp_port += 1
        elif _event is Event.BUMPER_CNTR:
            self._print_event(Fore.BLUE, _event, message.value)
            if self._triggered_bmp_cntr < self._limit:
                self._triggered_bmp_cntr += 1
        elif _event is Event.BUMPER_STBD:
            self._print_event(Fore.GREEN, _event, message.value)
            if self._triggered_bmp_stbd < self._limit:
                self._triggered_bmp_stbd += 1
        elif _event is Event.INFRARED_PORT_SIDE:
            self._print_event(Fore.RED, _event, message.value)
            if self._triggered_ir_port_side < self._limit:
                self._triggered_ir_port_side += 1
        elif _event is Event.INFRARED_PORT:
            self._print_event(Fore.RED, _event, message.value)
            if self._triggered_ir_port < self._limit:
                self._triggered_ir_port += 1
        elif _event is Event.INFRARED_CNTR:
            self._print_event(Fore.BLUE, _event, message.value)
            if self._triggered_ir_cntr < self._limit:
                self._triggered_ir_cntr += 1
        elif _event is Event.INFRARED_STBD:
            self._print_event(Fore.GREEN, _event, message.value)
            if self._triggered_ir_stbd < self._limit:
                self._triggered_ir_stbd += 1
        elif _event is Event.INFRARED_STBD_SIDE:
            self._print_event(Fore.GREEN, _event, message.value)
            if self._triggered_ir_stbd_side < self._limit:
                self._triggered_ir_stbd_side += 1
        else:
            self._log.info(Fore.BLACK + Style.BRIGHT + 'other event: {}'.format(_event.description))
        if _event != Event.CLOCK_TICK and _event != Event.CLOCK_TICK:
            self._log.info('passing message #{}; to superclass...'.format(message.number))
            super().handle(message)

    # ......................................................
    @property
    def all_triggered(self):
        return self._triggered_ir_port_side  >= self._limit \
            and self._triggered_ir_port      >= self._limit \
            and self._triggered_ir_cntr      >= self._limit \
            and self._triggered_ir_stbd      >= self._limit \
            and self._triggered_ir_stbd_side >= self._limit \
            and self._triggered_bmp_port     >= self._limit \
            and self._triggered_bmp_cntr     >= self._limit \
            and self._triggered_bmp_stbd     >= self._limit

    # ......................................................
    @property
    def count(self):
        return self._count

    def _get_output(self, color, label, value):
        if ( value == 0 ):
            _style = color + Style.BRIGHT
        elif ( value == 1 ):
            _style = color + Style.NORMAL
        elif ( value == 2 ):
            _style = color + Style.DIM
        else:
            _style = Fore.BLACK + Style.DIM
        return _style + self._fmt.format( label if ( value < self._limit ) else '' )

    # ..........................................................................
    def waiting_for_message(self):
        _div = Fore.CYAN + Style.NORMAL + ' | '
        self._log.info('waiting for: | ' \
                + self._get_output(Fore.RED, 'PSID', self._triggered_ir_port_side) \
                + _div \
                + self._get_output(Fore.RED, 'PORT', self._triggered_ir_port) \
                + _div \
                + self._get_output(Fore.BLUE, 'CNTR', self._triggered_ir_cntr) \
                + _div \
                + self._get_output(Fore.GREEN, 'STBD', self._triggered_ir_stbd) \
                + _div \
                + self._get_output(Fore.GREEN, 'SSID', self._triggered_ir_stbd_side) \
                + _div \
                + self._get_output(Fore.RED, 'BPRT', self._triggered_bmp_port) \
                + _div \
                + self._get_output(Fore.BLUE, 'BCNT', self._triggered_bmp_cntr) \
                + _div \
                + self._get_output(Fore.GREEN, 'BSTB', self._triggered_bmp_stbd) \
                + _div )

#EOF
