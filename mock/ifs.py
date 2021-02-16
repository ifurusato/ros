#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# Copyright 2020 by Murray Altheim. All rights reserved. This file is part of
# the Robot Operating System project and is released under the "Apache Licence,
# Version 2.0". Please see the LICENSE file included as part of this package.
#
# author:   Murray Altheim
# created:  2020-05-19
# modified: 2020-11-06
#
# A mock IFS that responds to key presses.
#

import sys, itertools
from threading import Thread
from colorama import init, Fore, Style
init()
try:
    import readchar
except ImportError:
    sys.exit(Fore.RED + "This script requires the readchar module.\nInstall with: sudo pip3 install readchar" + Style.RESET_ALL)

from lib.event import Event
from lib.message_factory import MessageFactory
from lib.logger import Logger, Level
from lib.rate import Rate

# ..............................................................................
class MockMessageBus():
    '''
    This message bus just displays IFS events as they arrive.
    '''
    def __init__(self, level):
        super().__init__()
        self._count = 0
        self._counter = itertools.count()
        self._log = Logger("message-bus", level)
        self._triggered_ir_port_side = self._triggered_ir_port  = self._triggered_ir_cntr  = self._triggered_ir_stbd  = \
        self._triggered_ir_stbd_side = self._triggered_bmp_port = self._triggered_bmp_cntr = self._triggered_bmp_stbd = 0
        self._limit = 3
        self._fmt = '{0:>9}'
        self._log.info('ready.')

    # ......................................................
    def handle(self, message):
        self._count = next(self._counter)
        message.number = self._count
        _event = message.event
        self._log.debug('added message #{}; priority {}: {}; event: {}'.format(message.number, message.priority, message.description, _event))
        if _event is Event.BUMPER_PORT:
            self._log.info(Fore.RED + Style.BRIGHT + 'BUMPER_PORT: {}; value: {}'.format(_event.description, message.value))
            if self._triggered_bmp_port < self._limit:
                self._triggered_bmp_port += 1
        elif _event is Event.BUMPER_CNTR:
            self._log.info(Fore.BLUE + Style.BRIGHT + 'BUMPER_CNTR: {}; value: {}'.format(_event.description, message.value))
            if self._triggered_bmp_cntr < self._limit:
                self._triggered_bmp_cntr += 1
        elif _event is Event.BUMPER_STBD:
            self._log.info(Fore.GREEN + Style.BRIGHT + 'BUMPER_STBD: {}; value: {}'.format(_event.description, message.value))
            if self._triggered_bmp_stbd < self._limit:
                self._triggered_bmp_stbd += 1
        elif _event is Event.INFRARED_PORT_SIDE:
            self._log.info(Fore.RED  + Style.BRIGHT + 'INFRARED_PORT_SIDE: {}; value: {}'.format(_event.description, message.value))
            if self._triggered_ir_port_side < self._limit:
                self._triggered_ir_port_side += 1
        elif _event is Event.INFRARED_PORT:
            self._log.info(Fore.RED  + Style.BRIGHT + 'INFRARED_PORT: {}; value: {}'.format(_event.description, message.value))
            if self._triggered_ir_port < self._limit:
                self._triggered_ir_port += 1
        elif _event is Event.INFRARED_CNTR:
            self._log.info(Fore.BLUE + Style.BRIGHT + 'INFRARED_CNTR:     distance: {:>5.2f}cm'.format(message.value))
            if self._triggered_ir_cntr < self._limit:
                self._triggered_ir_cntr += 1
        elif _event is Event.INFRARED_STBD:
            self._log.info(Fore.GREEN + Style.BRIGHT + 'INFRARED_STBD: {}; value: {}'.format(_event.description, message.value))
            if self._triggered_ir_stbd < self._limit:
                self._triggered_ir_stbd += 1
        elif _event is Event.INFRARED_STBD_SIDE:
            self._log.info(Fore.GREEN + Style.BRIGHT + 'INFRARED_STBD_SIDE: {}; value: {}'.format(_event.description, message.value))
            if self._triggered_ir_stbd_side < self._limit:
                self._triggered_ir_stbd_side += 1
        else:
            self._log.info(Fore.BLACK + Style.BRIGHT + 'other event: {}'.format(_event.description))

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

# ...............................................................
class MockIfs(object):
    '''
    A mock IFS.
    '''
    def __init__(self, level):
        super().__init__()
        self._log = Logger("mock-ifs", level)
        self._message_factory = MessageFactory(Level.INFO)
        self._message_bus = MockMessageBus(Level.INFO)
        self._rate    = Rate(10)
        self._thread  = None
        self._enabled = False
        self._closed  = False
        self._counter = itertools.count()
        self._log.info('ready.')

    # ..........................................................................
    def get_event_for_char(self, och):
        '''
        So far we're only mapping characters for IFS-based events:

           oct   dec   hex   char   usage
           141   97    61    a *    port side IR
           142   98    62    b      
           143   99    63    c *    cntr BMP
           144   100   64    d *    cntr IR
           145   101   65    e
           146   102   66    f *    stbd IR
           147   103   67    g *    stbd side IR
           150   104   68    h      
           151   105   69    i
           152   106   6A    j
           153   107   6B    k
           154   108   6C    l     
           155   109   6D    m
           156   110   6E    n  
           157   111   6F    o
           160   112   70    p
           161   113   71    q
           162   114   72    r
           163   115   73    s *    port IR
           164   116   74    t
           165   117   75    u
           166   118   76    v *    stbd BMP
           167   119   77    w
           170   120   78    x *    port BMP
           171   121   79    y
           172   122   7A    z
        '''
        if och   == 97:  # a
            return Event.INFRARED_PORT_SIDE 
        elif och == 99:  # c
            return Event.BUMPER_CNTR           
        elif och == 100: # d
            return Event.INFRARED_CNTR    
        elif och == 102: # f
            return Event.INFRARED_STBD   
        elif och == 103: # g
            return Event.INFRARED_STBD_SIDE 
        elif och == 115: # s
            return Event.INFRARED_PORT     
        elif och == 118: # v
            return Event.BUMPER_STBD          
        elif och == 120: # x
            return Event.BUMPER_PORT            
        else:
            return None

    # ..........................................................................
    @staticmethod
    def print_keymap():
        print(Fore.CYAN + '''
           
               o----------------------------------------
               |   A   |   S   |   D   |   F   |   G   |
         IR:   | PSID  | PORT  | CNTR  | STBD  | SSID  |
               o----------------------------------------
                           |   X   |   C   |   V   |
         BMP:              | PORT  | CNTR  | STBD  |
                           o-----------------------o

        ''' + Style.RESET_ALL)

    # ..........................................................................
    def fire_message(self, event):
        self._log.debug('firing message for event {}'.format(event))
        _message = self._message_factory.get_message(event, True)
        self._message_bus.handle(_message)
        if self._message_bus.all_triggered:
            return True
        else:
            self._message_bus.waiting_for_message()
            return False

    # ..........................................................................
    def _loop(self, f_is_enabled):
        self._log.info('start loop:\t' + Fore.YELLOW + 'type ' + Fore.RED + 'Delete ' + Fore.YELLOW + 'key to exit loop.')
        print('')
        while f_is_enabled():
            _count = next(self._counter)
            self._log.debug('[{:03d}]'.format(_count))
            ch  = readchar.readchar()
            och = ord(ch)
            if och == 91:
                break
            _event = self.get_event_for_char(och)
            if _event is not None:
                if self.fire_message(_event):
                    self._log.debug(Fore.YELLOW + '[{:03d}] COMPLETE.'.format(_count))
                    break
                else:
                    self._log.debug(Fore.YELLOW + '[{:03d}] "{}" ({}) pressed; event: {}'.format(_count, ch, och, _event))
            else:
                self._log.info(Fore.BLACK + Style.BRIGHT + '[{:03d}] unmapped key "{}" ({}) pressed.'.format(_count, ch, och))
            self._rate.wait()

        self._log.info('exit loop.')
        self.close()

    # ..........................................................................
    @property
    def enabled(self):
        return self._enabled

    # ..........................................................................
    def enable(self):
        if not self._closed:
            if self._enabled:
                self._log.warning('already enabled.')
            else:
                # if we haven't started the thread yet, do so now...
                if self._thread is None:
                    self._enabled = True
                    self._thread = Thread(name='mock-ifs', target=MockIfs._loop, args=[self, lambda: self.enabled], daemon=True)
                    self._thread.start()
                    self._log.info('enabled.')
                else:
                    self._log.warning('cannot enable: thread already exists.')
        else:
            self._log.warning('cannot enable: already closed.')

    # ..........................................................................
    def disable(self):
        if self._enabled:
            self._enabled = False
            self._thread = None
            self._log.info('disabled.')
        else:
            self._log.warning('already disabled.')

    # ..........................................................................
    def close(self):
        if not self._closed:
            if self._enabled:
                self.disable()
            self._closed = True
            self._log.info('closed.')
        else:
            self._log.warning('already closed.')

#EOF
