#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# Copyright 2020 by Murray Altheim. All rights reserved. This file is part of
# the Robot Operating System project and is released under the "Apache Licence,
# Version 2.0". Please see the LICENSE file included as part of this package.
#
# author:   Murray Altheim
# created:  2020-08-05
# modified: 2020-08-06
#
#  This class interprets the signals arriving from the 8BitDo N30 Pro gamepad,
#  a paired Bluetooth device. The result is printed to the console using the
# colorama library. To install colorama, type:
#
#   % sudo pip3 install colorama
#

import sys, traceback
from enum import Enum
from evdev import InputDevice, categorize, ecodes
from colorama import init, Fore, Style
init()


# ..............................................................................
class N30Control(Enum):
    '''
        An enumeration of the controls available on the N30 Pro, or any
        similar gamepad. The numeric values for 'code' may need to be
        modified for different models.
    '''
    A_BUTTON      = ( 1, 304,  'cross',    'A (Cross) Button')
    B_BUTTON      = ( 2, 305,  'circle',   'B (Circle) Button')
    X_BUTTON      = ( 3, 307,  'triangle', 'X (Triangle) Button')
    Y_BUTTON      = ( 4, 308,  'square',   'Y ((Square) Button')

    L1_BUTTON     = ( 5, 310,  'l1',       'L1 Button')
    L2_BUTTON     = ( 6, 312,  'l2',       'L2 Button')
    R1_BUTTON     = ( 7, 311,  'r1',       'R1 Button')
    R2_BUTTON     = ( 8, 313,  'r2',       'R2 Button')

    START_BUTTON  = ( 9, 315,  'start',    'Start Button')
    SELECT_BUTTON = ( 10, 314, 'select',   'Select Button')
    HOME_BUTTON   = ( 11, 306, 'home',     'Home Button')
    DPAD_HORIZ    = ( 12, 16,  'dph',      'D-PAD Horizontal')
    DPAD_VERT     = ( 13, 17,  'dpv',      'D-PAD Vertical')

    L3_VERT       = ( 14, 1,  'l3v',       'L3 Vertical')
    L3_HORIZ      = ( 15, 0,  'l3h',       'L3 Horizontal')
    R3_VERT       = ( 16, 5,  'r3v',       'R3 Vertical')
    R3_HORIZ      = ( 17, 2,  'r3h',       'R3 Horizontal')

    # ignore the first param since it's already set by __new__
    def __init__(self, num, code, name, label):
        self._code = code
        self._name = name
        self._label = label

    # this makes sure the code is read-only
    @property
    def code(self):
        return self._code

    # this makes sure the name is read-only
    @property
    def name(self):
        return self._name

    # this makes sure the label is read-only
    @property
    def label(self):
        return self._label


# ..............................................................................
def handleEvent(event):
    '''
        Handles the incoming event by filtering on event type and code.
    '''
    if event.type == ecodes.EV_KEY:
        if event.value == 1:
            if event.code == N30Control.Y_BUTTON.code:
                print(Fore.RED + "Y Button" + Style.RESET_ALL)
            elif event.code == N30Control.B_BUTTON.code:
                print(Fore.RED + "B Button" + Style.RESET_ALL)
            elif event.code == N30Control.A_BUTTON.code:
                print(Fore.RED + "A Button" + Style.RESET_ALL)
            elif event.code == N30Control.X_BUTTON.code:
                print(Fore.RED + "X Button" + Style.RESET_ALL)
            elif event.code == N30Control.L1_BUTTON.code:
                print(Fore.YELLOW + "L1 Button" + Style.RESET_ALL)
            elif event.code == N30Control.L2_BUTTON.code:
                print(Fore.YELLOW + "L2 Button" + Style.RESET_ALL)
            elif event.code == N30Control.R2_BUTTON.code:
                print(Fore.YELLOW + "R2 Button" + Style.RESET_ALL)
            elif event.code == N30Control.R1_BUTTON.code:
                print(Fore.YELLOW + "R1 Button" + Style.RESET_ALL)
            elif event.code == N30Control.START_BUTTON.code:
                print(Fore.GREEN + "Start Button" + Style.RESET_ALL)
            elif event.code == N30Control.SELECT_BUTTON.code:
                print(Fore.GREEN + "Select Button" + Style.RESET_ALL)
            elif event.code == N30Control.HOME_BUTTON.code:
                print(Fore.MAGENTA + "Home Button" + Style.RESET_ALL)
            else:
                print(Fore.BLACK + "event type: EV_KEY; event: {}; value: {}".format(event.code, event.value) + Style.RESET_ALL)
        else:
#               print(Fore.BLACK + Style.DIM + "event type: EV_KEY; value: {}".format(event.value) + Style.RESET_ALL)
            pass
    elif event.type == ecodes.EV_ABS:
        if event.code == N30Control.DPAD_HORIZ.code:
            if event.value == 1:
                print(Fore.CYAN + Style.BRIGHT + "D-Pad Horizontal(Right) {}".format(event.value) + Style.RESET_ALL)
            elif event.value == -1:
                print(Fore.CYAN + Style.NORMAL + "D-Pad Horizontal(Left) {}".format(event.value) + Style.RESET_ALL)
            else:
                print(Fore.BLACK + "D-Pad Horizontal(N) {}".format(event.value) + Style.RESET_ALL)
        elif event.code == N30Control.DPAD_VERT.code:
            if event.value == -1:
                print(Fore.CYAN + Style.NORMAL + "D-Pad Vertical(Up) {}".format(event.value) + Style.RESET_ALL)
            elif event.value == 1:
                print(Fore.CYAN + Style.BRIGHT + "D-Pad Vertical(Down) {}".format(event.value) + Style.RESET_ALL)
            else:
                print(Fore.BLACK + "D-Pad Vertical(N) {}".format(event.value) + Style.RESET_ALL)
        elif event.code == N30Control.L3_VERT.code:
            print(Fore.MAGENTA + "L3 Vertical {}".format(event.value) + Style.RESET_ALL)
        elif event.code == N30Control.L3_HORIZ.code:
            print(Fore.YELLOW + "L3 Horizontal {}".format(event.value) + Style.RESET_ALL)
        elif event.code == N30Control.R3_VERT.code:
            print(Fore.CYAN + "R3 Vertical {}".format(event.value) + Style.RESET_ALL)
        elif event.code == N30Control.R3_HORIZ.code:
            print(Fore.GREEN + "R3 Horizontal {}".format(event.value) + Style.RESET_ALL)
        else:
#           print(Fore.BLACK + "type: EV_ABS; event code: {}; value: {}".format(event.code, event.value) + Style.RESET_ALL)
            pass
    else:
#       print(Fore.BLACK + Style.DIM + "ZZ. event type: {}; code: {}; value: {}".format(event.type, event.code, event.value) + Style.RESET_ALL)
        pass


# main .........................................................................
def main(argv):

    try:

        _device_path = '/dev/input/event6'
        _gamepad = InputDevice(_device_path)

        #prints out device info at start
        print(Fore.WHITE + "gamepad: {}".format(_gamepad) + Style.RESET_ALL)

        # loop and filter by event code and print the mapped label
        for event in _gamepad.read_loop():
            handleEvent(event)

    except KeyboardInterrupt:
        print(Fore.RED + 'caught Ctrl-C; exiting...' + Style.RESET_ALL)
        sys.exit(0)
    except FileNotFoundError:
        print(Fore.RED + 'gamepad device not found (either not paired or not configured)' + Style.RESET_ALL)
        sys.exit(1)
    except Exception:
        print(Fore.RED + Style.BRIGHT + 'error processing gamepad events: {}'.format(traceback.format_exc()) + Style.RESET_ALL)
        sys.exit(1)


# call main ....................................................................
if __name__== "__main__":
    main(sys.argv[1:])


# EOF
