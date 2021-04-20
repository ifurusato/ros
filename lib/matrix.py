#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# Copyright 2020 by Murray Altheim. All rights reserved. This file is part of
# the Robot OS project and is released under the "Apache Licence, Version 2.0".
# Please see the LICENSE file included as part of this package.
#

import sys, time
import importlib.util
from threading import Thread
from colorama import init, Fore, Style
init()

from lib.logger import Level, Logger
from lib.i2c_scanner import I2CScanner
from lib.enums import Orientation
#from matrix11x7 import Matrix11x7

try:
    print('importing Matrix11x7...')
    from matrix11x7 import Matrix11x7
    from matrix11x7.fonts import font3x5
    _MATRIX11x7_IMPORTED = True
    print('imported Matrix11x7.')
except ImportError:
    print("This script requires the matrix11x7 module\nInstall with: pip3 install --user matrix11x7")
    _MATRIX11x7_IMPORTED = False

# ..............................................................................
class Matrices(object):
    '''
    Handles a port and starboard pair of 11x7 Matrix displays, accounting
    via an I2C scan on their availability.

    We go to a little trouble to permit zero, one or two matrix displays
    to be installed.
    '''

    LEFT  = 0
    RIGHT = 1
    UP    = 2
    DOWN  = 3

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
    def text(self, stbd_text, port_text, small_font=False):
        '''
        Display one or two characters (with no scrolling) on either or both
        displays. Call clear() to clear. The order of the arguments permits
        four characters to be displayed across the two displays, allowing
        four-letter words (the best kind).
        '''
        if self._port_matrix and port_text:
            self._port_matrix._text(port_text, small_font, False)
        if self._stbd_matrix and stbd_text:
            self._stbd_matrix._text(stbd_text, small_font, False)

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
        This uses no Threading, so it is blocking.

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
        This uses no Threading, so it is blocking.

        :param cols:     determines the number of columns to be lit
        '''
        self._log.debug('horizontal gradient...')   
        if self._port_matrix:
            self._port_matrix.gradient(-1, cols)
        if self._stbd_matrix:
            self._stbd_matrix.gradient(-1, cols)

    # ..........................................................................
    def wipe(self, direction, enable, delay_secs):
        '''
        When direction is LEFT or RIGHT, sequentially enables or disables the
        rows as a vertically-changing gradient, i.e., a horizontal movement.

        When direction is UP or DOWN, sequentially enables or disables the
        rows as a horizontally-changing gradient, i.e., a vertical movement.

        This creates a new thread.

        :param direction:    a value of LEFT, RIGHT, UP, or DOWN
        :param enable:       if true, enables (lightens) the displays; if false, disables (darkens)
        :param delay_secs:   the inter-row delay time in seconds
        '''
        if direction is Matrices.LEFT or direction is Matrices.RIGHT:
            self._thread = Thread(name='horiz-wipe', target=self._horizontal_wipe(direction, enable, delay_secs))
            self._thread.start()
        elif direction is Matrices.UP or direction is Matrices.DOWN:
            self._thread = Thread(name='vert-wipe', target=self._vertical_wipe(direction, enable, delay_secs))
            self._thread.start()
        else:
            raise Exception('unrecognised parameter for direction: {}'.format(direction))

    # ..........................................................................
    def _horizontal_wipe(self, direction, enable, delay_secs):
        '''
        Method called by thread.

        Wipe LEFT is not yet implemented.
        '''
        if direction is Matrices.RIGHT:
            self._log.info('matrix horizontal wipe right {}...'.format('on' if enable else 'off'))   
            r = [ 1, 12, 1 ] if enable else [10, 0, -1]
        else:
            self._log.info('matrix horizontal wipe left {}...'.format('on' if enable else 'off'))   
            raise NotImplementedError()
        for i in range(r[0], r[1], r[2]):
            self._log.debug('matrix at {:d}'.format(i))   
            if self._port_matrix:
                self._port_matrix.gradient(-1, i)
            if self._stbd_matrix:
                self._stbd_matrix.gradient(-1, i)
            time.sleep(delay_secs)

    # ..........................................................................
    def _vertical_wipe(self, direction, enable, delay_secs):
        '''
        Method called by thread.

        Wipe UP is not yet implemented.
        '''
        if direction is Matrices.DOWN:
            self._log.info('matrix vertical wipe down {}...'.format('on' if enable else 'off'))   
            r = [1, 8, 1] if enable else [7, 0, -1]
        else:
            self._log.info('matrix vertical wipe up {}...'.format('on' if enable else 'off'))   
            raise NotImplementedError()
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
        if _MATRIX11x7_IMPORTED:
            if orientation is Orientation.PORT:
                self._matrix11x7 = Matrix11x7(i2c_address=0x77)
            elif orientation is Orientation.STBD:
                self._matrix11x7 = Matrix11x7(i2c_address=0x75) # default
            else:
                raise Exception('unexpected value for orientation.')
            self._matrix11x7.set_brightness(0.4)
        else:
            self._matrix11x7 = None
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
        if not self._matrix11x7:
            self._log.debug('no matrix 11x7 display available.')
            return
        elif self._thread is None:
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
        if not self._matrix11x7:
            self._log.debug('no matrix 11x7 display available.')
            return
        self._matrix(self._matrix11x7.height, self._matrix11x7.width)

    # ..........................................................................
    def gradient(self, rows, cols):
        '''
        Turn on one or more rows of the LEDs at maximum brightness.

        Setting either argument to a negative or large number will
        automatically set it to the actual display size.
        :param rows:     determines how many rows to light (1-7)
        :param cols:     determines how many columns to light (1-11)
        '''
        if not self._matrix11x7:
            self._log.debug('no matrix 11x7 display available.')
            return
        _rows = min(self._matrix11x7.height, rows) if rows >= 0 else self._matrix11x7.height
        _cols = min(self._matrix11x7.width, cols) if cols >= 0 else self._matrix11x7.width
        self._matrix(_rows, _cols)

    # ..........................................................................
    def _matrix(self, rows, cols):
        '''
        Turn on the specified number of LED rows (1-7) and columns (1-11)
        at maximum brightness.
        '''
        if not self._matrix11x7:
            self._log.debug('no matrix 11x7 display available.')
            return
        elif self._thread is not None:
            self._log.warning('cannot continue: text thread is currently running.')
            return
        self._log.debug('matrix display ({},{})'.format(rows, cols))
        self._enabled = True
        self._matrix11x7.set_brightness(1.0)
        self._blank()
        for x in range(0, cols):
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
        if not self._matrix11x7:
            self._log.debug('no matrix 11x7 display available.')
            return
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
