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
# A mock Integrated Front Sensor (IFS) that responds to key presses. This expands
# the notion a bit, as rather than provide a second key-input mechanism, this one
# is also used for keyboard control of the mocked robot, i.e., it includes events
# unrelated to the original IFS.
#

import sys, asyncio, time, itertools
from threading import Thread
from colorama import init, Fore, Style
init()
try:
    import readchar
except ImportError:
    sys.exit(Fore.RED + "This script requires the readchar module.\nInstall with: pip3 install --user readchar" + Style.RESET_ALL)

from lib.event import Event
from lib.message_factory import MessageFactory
from lib.logger import Logger, Level
from lib.rate import Rate
from mock.message_bus import MockMessageBus

# ...............................................................
class MockIntegratedFrontSensor(object):
    '''
    A mock IFS.
    '''
    def __init__(self, message_bus, exit_on_complete=True, level=Level.INFO):
        super().__init__()
        self._log = Logger("mock-ifs", level)
        self._message_factory = MessageFactory(Level.INFO)
        self._message_bus = message_bus
#       self._message_bus = MockMessageBus(self, Level.INFO)
        self.exit_on_complete = exit_on_complete
#       self._rate     = Rate(10)
        self._thread   = None
        self._enabled  = False
        self._verbose  = True
        self._suppress = False
        self._closed   = False
        self._counter  = itertools.count()
        # .....
        self._triggered_ir_port_side = self._triggered_ir_port  = self._triggered_ir_cntr  = self._triggered_ir_stbd  = \
        self._triggered_ir_stbd_side = self._triggered_bmp_port = self._triggered_bmp_cntr = self._triggered_bmp_stbd = 0
        self._limit = 3
        self._fmt = '{0:>9}'
        self._log.info('ready.')

    # ..........................................................................
    def name(self):
        return 'MockIntegratedFrontSensor'

    # ..........................................................................
    def suppress(self, mode):
        '''
        Enable or disable capturing characters. Upon starting the loop the
        suppress flag is set False, but can be enabled or disabled as
        necessary without halting the thread.
        '''
        self._suppress = mode

    # ..........................................................................
    def _loop(self, f_is_enabled):
        self._log.info('start loop:\t' + Fore.YELLOW + 'type the \"' + Fore.RED + 'Delete' + Fore.YELLOW \
                + '\" or \"' + Fore.RED + 'q' + Fore.YELLOW + '\" key to exit sensor loop, the \"' \
                + Fore.RED + 'h' + Fore.YELLOW + '\" key for help.')
        print('\n')
        while f_is_enabled():
            if self._suppress: # then just sleep during the loop
                time.sleep(0.2)
            else:
                _count = next(self._counter)
                self._log.debug('[{:03d}]'.format(_count))
                ch  = readchar.readchar()
                och = ord(ch)
                if och == 91 or och == 113 or och == 127: # 'q' or delete
                    break
                elif och == 104: # 'h' for help
                    self.print_keymap()
                    continue
                elif och == 109: # 'j' to toggle messages sent to IFS
                    self._verbose = not self._verbose
                    self._log.info(Fore.YELLOW + 'setting verbose mode to: {}'.format(self._verbose))
                _event = self.get_event_for_char(och)
                if _event is not None:

#                   self._log.info('firing message for event {}'.format(event))
#                   _message = self._message_factory.get_message(event, True)
#                   self._message_bus.publish(_message)
#                   await asyncio.sleep(0.1)

                    self.fire_message(_event)
                    if self.exit_on_complete:
                        self._log.debug('[{:03d}] COMPLETE.'.format(_count))
                        break
                    else:
                        self._log.debug('[{:03d}] "{}" ({}) pressed; event: {}'.format(_count, ch, och, _event))
                    if self.all_triggered:
                        break
                    elif self._verbose:
                        self.waiting_for_message()
                else:
                    self._log.info('[{:03d}] unmapped key "{}" ({}) pressed.'.format(_count, ch, och))
                self._rate.wait()

        self._log.info(Fore.YELLOW + 'exit loop.')

    # ..........................................................................
    async def fire_message(self, event):
        self._log.debug('firing message for event {}'.format(event))
        _message = self._message_factory.get_message(event, True)
        self._message_bus.publish(_message)
        await asyncio.sleep(0.1)

    # message handling .........................................................

    # ......................................................
    def process_message(self, message):
        '''
        Processes the message, keeping count and providing a display of status.
        '''
        _event = message.event
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

    # ......................................................
    def _print_event(self, color, event, value):
        self._log.info('event:\t' + color + Style.BRIGHT + '{}; value: {}'.format(event.description, value))

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

    # ......................................................
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
                    self._thread = Thread(name='mock-ifs', target=MockIntegratedFrontSensor._loop, args=[self, lambda: self.enabled], daemon=True)
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

    # ..........................................................................
    def print_keymap(self):
#        1         2         3         4         5         6         7         8         9         C         1         2
#23456789012345678901234567890123456789012345678901234567890123456789012345678901234567890123456789012345678901234567890
        self._log.info('''key map:
           
    o-------------------------------------------------o                                                    ---o--------o
    |    Q    |                             |    T    |                                                       |   DEL  |
    |  QUIT   |                             |  NOOP   |                                                       |  QUIT  |
    o--------------------------------------------------------------------------o---------o                 ---o--------o
         |    A    |    S    |    D    |    F    |    G    |    H    |    J    |    K    |
         | IR_PSID | IR_PORT | IR_CNTR | IR_STBD | IR_SSID |  HELP   |         |         |
         o-------------------------------------------------------------------------------o------------------------o
              |    X    |    C    |    V    |                                       |    M    |    <    |    >    |
              | BM_PORT | BM_CNTR | BM_STBD |                                       | TOG_MSG | DN_VELO | UP_VELO |
              o-----------------------------o                                       o-----------------------------o

        ''')
        self._log.info('note:\t' + Fore.YELLOW + 'will exit after receiving 3 events on each sensor.')
        print('')

    # ..........................................................................
    def get_event_for_char(self, och):
        '''
        Below are the mapped characters for IFS-based events, including several others:

           oct   dec   hex   char   usage

            54   44    2C    ,      increase motors speed (both)
            56   46    2E    .      decrease motors speed (both)

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
           155   109   6D    m      toggle IFS messaging
           156   110   6E    n  
           157   111   6F    o
           160   112   70    p
           161   113   71    q
           162   114   72    r
           163   115   73    s *    port IR
           164   116   74    t *    noop (test message)
           165   117   75    u
           166   118   76    v *    stbd BMP
           167   119   77    w
           170   120   78    x *    port BMP
           171   121   79    y
           172   122   7A    z

        '''
        if och   == 44:  # ,
            return Event.DECREASE_SPEED 
        elif och   == 46:  # .
            return Event.INCREASE_SPEED 
        elif och   == 97:  # a
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
        elif och == 116: # s
            return Event.NOOP     
        elif och == 118: # v
            return Event.BUMPER_STBD          
        elif och == 120: # x
            return Event.BUMPER_PORT            
        else:
            return None

#EOF
