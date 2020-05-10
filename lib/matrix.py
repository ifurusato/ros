#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# Copyright 2020 by Murray Altheim. All rights reserved. This file is part of
# the Robot OS project and is released under the "Apache Licence, Version 2.0".
# Please see the LICENSE file included as part of this package.
#

import sys, time, threading
from colorama import init, Fore, Style
init()

from lib.logger import Level, Logger
try:
    from matrix11x7 import Matrix11x7
    from matrix11x7.fonts import font3x5
except ImportError:
#   print(Fore.MAGENTA + 'failed to import matrix11x7, using mock...' + Style.RESET_ALL)
#   from .mock_matrix11x7 import Matrix11x7
    print(Fore.MAGENTA + 'failed to import matrix11x7, exiting...' + Style.RESET_ALL)
    sys.exit(1)


class Matrix():
    '''
        This class provides access to a Pimoroni 11x7 LED Matrix display, whose
        LEDs are all white. This is located at the default 0x75 address.

        This provides a threaded text display, as well as using the matrix as a
        light source.
    '''
    def __init__(self, level):
        self._log = Logger("matrix", level)
        self._matrix11x7 = Matrix11x7()
        self._matrix11x7.set_brightness(0.4)
        self._is_enabled = False
        self._screens = 0
        self._thread = None
        self._log.info('ready.')


    # ..........................................................................
    def text(self, message, is_small_font, is_scrolling):
        '''
            Display the message. If 'is_small_font' use a smaller font;
            if 'is_scrolling' is true, scroll the display. If scrolling
            is true this will continue to scroll until disable() is
            called.
        '''
        if self._thread is None:
            self._thread = threading.Thread(target=Matrix._text, args=[self, message, is_small_font, is_scrolling])
            self._thread.start()
        else:
            self._log.debug('thread already running; replacing existing text in buffer.')
            self._matrix11x7.clear()
            if is_small_font:
                self._matrix11x7.write_string(message, y=1, font=font3x5)
            else:
                self._matrix11x7.write_string(message)


    # ..........................................................................
    def get_screens(self):
        '''
            Returns the number of screens of text that have been displayed
            since the text thread has started. E.g., the value will be 0
            until the text has been displayed once.
        '''
        return self._screens


    # ..........................................................................
    def _text(self, message, is_small_font, is_scrolling):
        self._is_enabled = True
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
            while self._is_enabled:
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
    def light(self):
        '''
            Turn on all of the LEDs at maximum brightness.
        '''
        if self._thread is not None:
            self._log.info('cannot continue: text thread is currently running.')
            return
        self._is_enabled = True
        self._matrix11x7.set_brightness(1.0)
        for x in range(0, self._matrix11x7.width):
            for y in range(0, self._matrix11x7.height):
                v = 0.7
                self._matrix11x7.pixel(x, y, v)
        self._matrix11x7.show()


    # ..........................................................................
    def clear(self):
        '''
            Turn off all LEDs.
        '''
        self._matrix11x7.set_brightness(0.5)
        for x in range(0, self._matrix11x7.width):
            for y in range(0, self._matrix11x7.height):
                v = 0.7
                self._matrix11x7.pixel(x, y, 0.0)
        self._matrix11x7.show()


    # ..........................................................................
    def disable(self):
        '''
            Disable any actions currently looping.
        '''
        self._is_enabled = False
        if self._thread != None:
            self._thread.join()
            self._thread = None


    # ..........................................................................
    def close(self):
        self.disable()
        self.clear()


#EOF
