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
# A mock Integrated Front Sensor (IFS) that responds to key presses.
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
from mock.message_bus import MockMessageBus

# ...............................................................
class MockIntegratedFrontSensor(object):
    '''
    A mock IFS.
    '''
    def __init__(self, exit_on_complete=True, level=Level.INFO):
        super().__init__()
        self._log = Logger("mock-ifs", level)
        self._message_factory = MessageFactory(Level.INFO)
        self._message_bus = MockMessageBus(Level.INFO)
        self.exit_on_complete = exit_on_complete
        self._rate     = Rate(10)
        self._thread   = None
        self._enabled  = False
        self._suppress = False
        self._closed   = False
        self._counter  = itertools.count()
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
            if self._suppress:
                time.sleep(1.0)
            else:
                _count = next(self._counter)
                self._log.debug('[{:03d}]'.format(_count))
                ch  = readchar.readchar()
                och = ord(ch)
                if och == 91 or och == 113 or och == 127:
                    break
                elif och == 104:
                    self.print_keymap()
                    continue
                _event = self.get_event_for_char(och)
                if _event is not None:
                    if self.fire_message(_event) and self.exit_on_complete:
                        self._log.debug('[{:03d}] COMPLETE.'.format(_count))
                        break
                    else:
                        self._log.debug('[{:03d}] "{}" ({}) pressed; event: {}'.format(_count, ch, och, _event))
                else:
                    self._log.info('[{:03d}] unmapped key "{}" ({}) pressed.'.format(_count, ch, och))
                self._rate.wait()

        self._log.info(Fore.YELLOW + 'exit loop.')

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
        self._log.info('''key map:
           
               o----------------------------------------
               |   A   |   S   |   D   |   F   |   G   |
         IR:   | PSID  | PORT  | CNTR  | STBD  | SSID  |
               o----------------------------------------
                           |   X   |   C   |   V   |
         BMP:              | PORT  | CNTR  | STBD  |
                           o-----------------------o

        ''')
        self._log.info('note:\t' + Fore.YELLOW + 'will exit after receiving 3 events on each sensor.')
        print('')

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

#EOF
