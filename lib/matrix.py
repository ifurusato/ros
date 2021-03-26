#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# Copyright 2020 by Murray Altheim. All rights reserved. This file is part of
# the Robot OS project and is released under the "Apache Licence, Version 2.0".
# Please see the LICENSE file included as part of this package.
#

import sys, time
from threading import Thread
from colorama import init, Fore, Style
init()

from lib.logger import Level, Logger
from lib.i2c_scanner import I2CScanner
from lib.enums import Orientation
#from matrix11x7 import Matrix11x7

IMPORTED = False

def import_matrix11x7():
    global IMPORTED
    if not IMPORTED:
        try:
            print('importing Matrix11x7...')
            from matrix11x7 import Matrix11x7
            from matrix11x7.fonts import font3x5
            IMPORTED = True
            print('imported Matrix11x7.')
        except ImportError:
            sys.exit("This script requires the matrix11x7 module\nInstall with: pip3 install --user matrix11x7")

# ..............................................................................
class Matrices(object):
    '''
    Handles a port and starboard pair of 11x7 Matrix displays, accounting
    via an I2C scan on their availability.
    '''
    def __init__(self, level):
        self._log = Logger("matrices", level)
        _i2c_scanner = I2CScanner(Level.DEBUG)
        self._enabled = True
        if _i2c_scanner.has_address([0x77]): # port
            self._port_matrix = Matrix(Orientation.PORT, Level.INFO)
            self._log.info('port-side matrix available.')
        else:
            self._port_matrix = None
            self._log.warning('no port-side matrix available.')
        if _i2c_scanner.has_address([0x75]): # starboard
            self._stbd_matrix = Matrix(Orientation.STBD, Level.INFO)
            self._log.info('starboard-side matrix available.')
        else:
            self._stbd_matrix = None
            self._log.warning('no starboard-side matrix available.')

        if not self._port_matrix and not self._stbd_matrix:
            self._enabled = False
            self._log.warning('no matrix displays available.')
        self._log.info('ready.')

    # ..........................................................................
    def text(self, port_text, stbd_text):
        '''
        Display one or two characters (with no scrolling) on either or both
        displays. Call clear() or call with space characters to clear.
        '''
        if self._port_matrix and port_text:
            self._port_matrix.text(port_text, False, False)
        if self._stbd_matrix and stbd_text:
            self._stbd_matrix.text(stbd_text, False, False)

    # ..........................................................................
    def get_matrix(self, orientation):
        if orientation == Orientation.PORT:
            return self._port_matrix
        if orientation == Orientation.STBD:
            return self._stbd_matrix

    # ..........................................................................
    def on(self):
        '''
        Turns the lights on, i.e., enables all LEDs in each matrix.
        '''
        self._log.debug('matrix on...')   
        if self._port_matrix:
            self._port_matrix.on()
        if self._stbd_matrix:
            self._stbd_matrix.on()

    # ..........................................................................
    def vertical_gradient(self, rows):
        '''
        Set the displays to a vertically-changing gradient.

        :param rows:     determines the number of rows to be lit
        '''
        self._log.debug('vertical gradient...')   
        if self._port_matrix:
            self._port_matrix.gradient(rows, -1)
        if self._stbd_matrix:
            self._stbd_matrix.gradient(rows, -1)

    # ..........................................................................
    def horizontal_gradient(self, cols):
        '''
        Set the displays to a horizontally-changing gradient.

        :param cols:     determines the number of columns to be lit
        '''
        self._log.debug('horizontal gradient...')   
        if self._port_matrix:
            self._port_matrix.gradient(-1, cols)
        if self._stbd_matrix:
            self._stbd_matrix.gradient(-1, cols)

    # ..........................................................................
    def blink(self, enable, delay_secs):
        '''
        Sequentially enables or disables the rows as a horizontally-changing gradient.

        :param enable:       if true, enables (lightens) the displays; if false, disables (darkens)
        :param delay_secs:   the inter-row delay time in seconds
        '''
        self._log.debug('matrix blink {}...'.format('on' if enable else 'off'))   
        r = [ 1, 8, 1 ] if enable else [7, 0, -1 ]
        for i in range(r[0], r[1], r[2]):
            self._log.debug('matrix at {:d}'.format(i))   
            if self._port_matrix:
                self._port_matrix.gradient(i, -1)
            if self._stbd_matrix:
                self._stbd_matrix.gradient(i, -1)
            time.sleep(delay_secs)

    # ..........................................................................
    def clear(self):
        '''
        Turns the lights off and disables any running threads.
        '''
        self._log.debug('clear.')
        if self._port_matrix:
            self._port_matrix.disable()
            self._port_matrix.clear()
        if self._stbd_matrix:
            self._stbd_matrix.disable()
            self._stbd_matrix.clear()

# ..............................................................................
class Matrix(object):
    '''
    This class provides access to a Pimoroni 11x7 LED Matrix display, whose
    LEDs are all white. This is located at the default 0x75 address.

    This provides a threaded text display, as well as using the matrix as a
    light source.
    '''
    def __init__(self, orientation, level):
        self._log = Logger("matrix", level)
        if orientation is Orientation.PORT:
            import_matrix11x7()
            self._matrix11x7 = Matrix11x7(i2c_address=0x77)
        elif orientation is Orientation.STBD:
            import_matrix11x7()
            self._matrix11x7 = Matrix11x7(i2c_address=0x75) # default
        else:
            raise Exception('unexpected value for orientation.')
        self._matrix11x7.set_brightness(0.4)
        self._enabled = False # used only for Threaded processes
        self._screens = 0
        self._thread = None
        self._log.info('ready.')

    # ..........................................................................
    def text(self, message, is_small_font, is_scrolling):
        '''
        Display the message using a Thread. If 'is_small_font' use a smaller
        font; if 'is_scrolling' is true, scroll the display. If scrolling is
        true this will continue to scroll until disable() is called.
        '''
        if self._thread is None:
            self._thread = Thread(name='matrix', target=Matrix._text, args=[self, message, is_small_font, is_scrolling])
            self._thread.start()
        else:
            self._log.debug('thread already running; replacing existing text in buffer.')
            self._matrix11x7.clear()
            if is_small_font:
                self._matrix11x7.write_string(message, y=1, font=font3x5)
            else:
                self._matrix11x7.write_string(message)

    # ..........................................................................
    def _text(self, message, is_small_font, is_scrolling):
        '''
        Displays the message on the matrix display.
        '''
        self._enabled = True
        _scroll = 0
        self._screens = 0
        _message = message if not is_scrolling else message + ' '
        if is_small_font:
            self._matrix11x7.write_string(_message, y=1, font=font3x5)
        else:
            self._matrix11x7.write_string(_message)
        _buf_width = self._matrix11x7.get_buffer_shape()[0]
        if is_scrolling:
            # scroll the buffer content
            while self._enabled:
                self._matrix11x7.show()
                self._matrix11x7.scroll() # scrolls 1 position horizontally
                _scroll += 1
                if ( _scroll % _buf_width ) == 0:
                    self._screens += 1
                    self._log.info('{:d} screens ({:d}); buffer width: {}.'.format(self._screens, _scroll, _buf_width))
                time.sleep(0.1)
#               time.sleep(1.0)
        else:
            self._matrix11x7.show()

    # ..........................................................................
    def get_screens(self):
        '''
        Returns the number of screens of text that have been displayed
        since the text thread has started. E.g., the value will be 0
        until the text has been displayed once.
        '''
        return self._screens

    # ..........................................................................
    def on(self):
        '''
        Turn on all of the LEDs at maximum brightness.
        '''
        self._matrix(self._matrix11x7.height, self._matrix11x7.width)
#       self._matrix11x7.width
#       self._matrix11x7.height

    # ..........................................................................
    def gradient(self, rows, cols):
        '''
        Turn on one or more rows of the LEDs at maximum brightness.

        Setting either argument to a negative or large number will
        automatically set it to the actual display size.
        :param rows:     determines how many rows to light (1-7)
        :param cols:     determines how many columns to light (1-11)
        '''
        _rows = min(self._matrix11x7.height, rows) if rows > 0 else self._matrix11x7.height
        _cols = min(self._matrix11x7.width, cols) if cols > 0 else self._matrix11x7.width
        self._matrix(_rows, _cols)

    # ..........................................................................
    def _matrix(self, rows, cols):
        '''
        Turn on the specified number of LED rows (1-7) and columns (1-11)
        at maximum brightness.
        '''
        if self._thread is not None:
            self._log.warning('cannot continue: text thread is currently running.')
            return
        self._log.debug('matrix display ({},{})'.format(rows, cols))
        self._enabled = True
        self._matrix11x7.set_brightness(1.0)
        self._blank()
        for x in range(0, cols):
#       for x in range(0, self._matrix11x7.width):
#           for y in range(0, self._matrix11x7.height):
            for y in range(0, rows):
                v = 0.7
                self._matrix11x7.pixel(x, y, v)
        self._matrix11x7.show()

    # ..........................................................................
    def _blank(self):
        '''
        Turn off all LEDs but don't show the change.
        '''
        self._matrix11x7.set_brightness(0.5)
        for x in range(0, self._matrix11x7.width):
            for y in range(0, self._matrix11x7.height):
                v = 0.7
                self._matrix11x7.pixel(x, y, 0.0)

    # ..........................................................................
    def clear(self):
        '''
        Turn off all LEDs.
        '''
        self._blank()
        self._matrix11x7.show()

    # ..........................................................................
    def disable(self):
        '''
        Disable any actions currently looping. This does not disable the
        display itself.
        '''
        self._enabled = False
        if self._thread != None:
            self._thread.join()
            self._thread = None

    # ..........................................................................
    def close(self):
        self.disable()
        self.clear()

#EOF
