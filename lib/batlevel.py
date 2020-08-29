#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# Copyright 2020 by Murray Altheim. All rights reserved. This file is part of
# the Robot OS project and is released under the "Apache Licence, Version 2.0".
# Please see the LICENSE file included as part of this package.
#
# author:   Murray Altheim
# created:  2020-04-27
# modified: 2020-05-21
#
# Uses the ThunderBorg RGB LED to indicate the battery level of a Makita 18V 
# Lithium-Ion power tool battery, whose actual top voltage is around 20 volts.
# This uses a thread, and when it's done reverts the RGB LED back to is original
# indicator as the input battery voltage of the ThunderBorg. This is generally
# the same value but this class enumerates the value so that its state is more 
# obvious.
#

import os, sys, time, traceback
from threading import Thread
from enum import Enum
from colorama import init, Fore, Style
init()

import lib.ThunderBorg3 as ThunderBorg
from lib.logger import Logger, Level

# ..............................................................................
class Color(Enum):
    RED       = ( 0, 'red',       1.0, 0.0, 0.0 )
    ORANGE    = ( 1, 'amber',     0.6, 0.1, 0.0 )
    AMBER     = ( 2, 'orange',    0.8, 0.2, 0.0 )
    YELLOW    = ( 3, 'yellow',    0.9, 0.8, 0.0 )
    GREEN     = ( 4, 'green',     0.0, 1.0, 0.0 )
    TURQUOISE = ( 5, 'turquoise', 0.0, 1.0, 0.3 )
    CYAN      = ( 6, 'cyan',      0.0, 1.0, 1.0 )
    MAGENTA   = ( 7, 'magenta',   0.9, 0.0, 0.9 )
    BLACK     = ( 8, 'black',     0.0, 0.0, 0.0 )

    # ignore the first param since it's already set by __new__
    def __init__(self, num, name, red, green, blue):
        self._name = name
        self._red = red
        self._green = green
        self._blue = blue

    @property
    def name(self):
        return self._name

    @property
    def red(self):
        return self._red

    @property
    def green(self):
        return self._green

    @property
    def blue(self):
        return self._blue


# ..............................................................................
class BatteryLevelIndicator():
    '''
        Battery level indicator for a Makita power tool battery, with typical readings:

          # one bar:   16.648v
          # two bars:  17.385v
          # four bars: 20.016v

        This has a fixed loop time of 15 seconds.
    '''
    def __init__(self, level):
        super().__init__()
        self._log = Logger("batlev", Level.INFO)
        TB = ThunderBorg.ThunderBorg(Level.INFO)
        TB.Init()
        if not TB.foundChip:
            boards = ThunderBorg.ScanForThunderBorg()
            if len(boards) == 0:
                raise Exception('no thunderborg found, check you are attached.')
            else:
                raise Exception('no ThunderBorg at address {:02x}, but we did find boards:'.format(TB.i2cAddress))
        self._tb = TB
        self._enabled = False
        self._thread = None
        self._loop_delay_sec = 15.0
        self._log.info('ready.')

    # ................................................................
    def _battery_loop(self):
        self._log.info('starting battery indicator loop...')
        while self._enabled:
            _voltage = self._tb.GetBatteryReading()
            if _voltage is None:
                _color = Color.MAGENTA # error color
            else:
                _color = self._get_color_for_voltage(_voltage)
                if _color is Color.RED or _color is Color.ORANGE:
                    self._log.info(Fore.RED + 'main battery: {:>5.2f}V'.format(_voltage))
                elif _color is Color.AMBER or _color is Color.YELLOW:
                    self._log.info(Fore.YELLOW + 'main battery: {:>5.2f}V'.format(_voltage))
                elif _color is Color.GREEN or _color is Color.TURQUOISE:
                    self._log.info(Fore.GREEN + 'main battery: {:>5.2f}V'.format(_voltage))
                elif _color is Color.CYAN:
                    self._log.info(Fore.CYAN + 'main battery: {:>5.2f}V'.format(_voltage))
            self._tb.SetLed1( _color.red, _color.green, _color.blue )
            time.sleep(self._loop_delay_sec) 

    # ................................................................
    def is_enabled(self):
        return self._enabled

    # ................................................................
    def enable(self):
        if self._thread is None:
            self._tb.SetLedShowBattery(False)
            self._thread = Thread(target=self._battery_loop, args=( ))
            self._enabled = True
            self._thread.start()
            self._log.info('enabled.')
        else:
            self._log.warn('thread already exists: cannot enable.')

    # ................................................................
    def disable(self):
        self._enabled = False
        if self._thread is not None:
            self._log.info('disabling...')
            _color = Color.BLACK
            self._tb.SetLed1( _color.red, _color.green, _color.blue )
            self._thread.join(timeout=1.0)
            self._thread = None
            self._tb.SetLedShowBattery(True)
        self._log.info('disabled.')

    # ..............................................................................
    def _get_color_for_voltage(self, voltage):
        if ( voltage > 20.0 ):
            return Color.CYAN
        elif ( voltage > 19.0 ):
            return Color.TURQUOISE
        elif ( voltage > 18.8 ):
            return Color.GREEN
        elif ( voltage > 18.0 ):
            return Color.YELLOW
        elif ( voltage > 17.0 ):
            return Color.AMBER
        elif ( voltage > 16.0 ):
            return Color.ORANGE
        else:
            return Color.RED
    
# main .........................................................................

_ble = None

def main(argv):

    try:

        _ble = BatteryLevelIndicator(Level.INFO)
        _ble.enable()

        while _ble.is_enabled():
            print(Fore.BLACK + Style.DIM + '.' + Style.RESET_ALL)
            time.sleep(10.0)
        
        print(Fore.BLACK + Style.DIM + 'done.' + Style.RESET_ALL)
        
    except KeyboardInterrupt:
        if _ble is not None:
            _ble.disable()
        print(Fore.BLACK + Style.DIM + 'Ctrl-C caught, exiting...' + Style.RESET_ALL)
    except Exception as e:
        if _ble is not None:
            _ble.disable()
        print(Fore.RED + Style.BRIGHT + 'error in battery level indicator: {}'.format(e))
        traceback.print_exc(file=sys.stdout)
    finally:
        print(Fore.BLACK + 'finally.' + Style.RESET_ALL)


# call main ....................................................................
if __name__== "__main__":
    main(sys.argv[1:])

#EOF
