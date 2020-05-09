#!/usr/bin/env python3

import sys, time, colorsys, threading
from enum import Enum

try:
    import numpy
except ImportError:
    sys.exit("This script requires the numpy module\nInstall with: sudo pip3 install numpy")

from lib.logger import Level, Logger
from lib.feature import Feature
from lib.enums import Color
from rgbmatrix5x5 import RGBMatrix5x5


# ..............................................................................
class DisplayType(Enum):
    RAINBOW = 1
    BLINKY  = 2
    SCAN    = 3
    RANDOM  = 4
    DARK    = 5


# ..............................................................................
class RgbMatrix(Feature):
    '''
        This class provides access to a pair of Pimoroni 5x5 RGB LED Matrix displays,
        labeled port and starboard. It also includes several canned demonstrations,
        which can be used to indicate behaviours in progress.
    '''
    def __init__(self, level):
        global enabled
        self._log = Logger("rgbmatrix", level)
        self._rgbmatrix5x5_PORT = RGBMatrix5x5(address=0x77)
        self._log.info('port rgbmatrix at 0x77.')
        self._rgbmatrix5x5_PORT.set_brightness(0.8)
        self._rgbmatrix5x5_PORT.set_clear_on_exit()
        self._rgbmatrix5x5_STBD = RGBMatrix5x5(address=0x74)
        self._log.info('starboard rgbmatrix at 0x74.')
        self._rgbmatrix5x5_STBD.set_brightness(0.8)
        self._rgbmatrix5x5_STBD.set_clear_on_exit()
        self._height = self._rgbmatrix5x5_PORT.height
        self._width  = self._rgbmatrix5x5_PORT.width
        self._thread_PORT = None
        self._thread_STBD = None
        enabled = False
        self._closing = False
        self._closed = False
        self._display_type = DisplayType.DARK # default
        self._log.info('ready.')


    # ..........................................................................
    def name(self):
        return 'RgbMatrix'


    # ..........................................................................
    def _get_target(self):
        if self._display_type is DisplayType.RAINBOW:
            return RgbMatrix._rainbow
        elif self._display_type is DisplayType.BLINKY:
            return RgbMatrix._blinky
        elif self._display_type is DisplayType.RANDOM:
            return RgbMatrix._random
        elif self._display_type is DisplayType.SCAN:
            return RgbMatrix._scan
        elif self._display_type is DisplayType.DARK:
            return RgbMatrix._dark


    # ..........................................................................
    def enable(self):
        global enabled
        if not self._closed and not self._closing:
            if self._thread_PORT is None and self._thread_STBD is None:
                enabled = True
                self._thread_PORT = threading.Thread(target=self._get_target(), args=[self, self._rgbmatrix5x5_PORT])
                self._thread_PORT.start()
                self._thread_STBD = threading.Thread(target=self._get_target(), args=[self, self._rgbmatrix5x5_STBD])
                self._thread_STBD.start()
                self._log.info('enabled.')
            else:
                self._log.warning('cannot enable: process already running.')
        else:
            self._log.warning('cannot enable: already closed.')


    # ..........................................................................
    def clear(self):
        self._clear(self._rgbmatrix5x5_PORT)
        self._clear(self._rgbmatrix5x5_STBD)


    # ..........................................................................
    def is_disabled(self):
        global enabled
        return not enabled


    # ..........................................................................
    def disable(self):
        global enabled
        self._log.info('disabling...')
        enabled = False
        self._clear(self._rgbmatrix5x5_PORT)
        self._clear(self._rgbmatrix5x5_STBD)
        if self._thread_PORT != None:
            self._thread_PORT.join(timeout=1.0)
            self._log.debug('port rgbmatrix thread joined.')
            self._thread_PORT = None
        if self._thread_STBD != None:
            self._thread_STBD.join(timeout=1.0)
            self._log.debug('starboard rgbmatrix thread joined.')
            self._thread_STBD = None
        self._log.info('disabled.')


    # ..........................................................................
    def _rainbow(self, rgbmatrix5x5):
        '''
            Display a rainbow pattern.
        '''
        global enabled
        self._log.info('starting rainbow...')
        _spacing = 360.0 / 5.0
        _hue = 0
        while enabled:
            for x in range(self._width):
                for y in range(self._height):
                    _hue = int(time.time() * 100) % 360
                    offset = (x * y) / 25.0 * _spacing
                    h = ((_hue + offset) % 360) / 360.0
                    r, g, b = [int(c * 255) for c in colorsys.hsv_to_rgb(h, 1.0, 1.0)]
                    rgbmatrix5x5.set_pixel(x, y, r, g, b)
#                   r, g, b = [int(c * 255) for c in colorsys.hsv_to_rgb(h + 0.5, 1.0, 1.0)]
#                   rainbow2.set_pixel(x, y, r, g, b)
                if not enabled:
                    break
            rgbmatrix5x5.show()
#           rainbow2.show()
            time.sleep(0.0001)
        self._clear(rgbmatrix5x5)
        self._log.info('rainbow ended.')


    # ..........................................................................
    def _dark(self, rgbmatrix5x5):
        '''
            Display a dark static color.
        '''
        global enabled
        self._log.info('starting dark...')
        self.set_color(Color.BLACK)
        while enabled:
            time.sleep(0.2)


    # ..........................................................................
    @staticmethod
    def make_gaussian(fwhm):
        x = numpy.arange(0, 5, 1, float)
        y = x[:, numpy.newaxis]
        x0, y0 = 2, 2
        fwhm = fwhm
        gauss = numpy.exp(-4 * numpy.log(2) * ((x - x0) ** 2 + (y - y0) ** 2) / fwhm ** 2)
        return gauss


    # ..........................................................................
    def _blinky(self, rgbmatrix5x5):
        '''
            Display a pair of blinky spots.
        '''
        global enabled
        self._log.info('starting blinky...')
        if self._height == self._width:
            _delta = 0
        else:
            _delta = 2

        while enabled:
            for i in range(3):
                for z in list(range(1, 10)[::-1]) + list(range(1, 10)):
                    fwhm = 5.0/z
                    gauss = RgbMatrix.make_gaussian(fwhm)
                    start = time.time()
                    for y in range(self._height):
                        for x in range(self._width):
                            h = 0.5
                            s = 0.8
                            if self._height <= self._width:
                                v = gauss[x, y]
#                               v = gauss[x, y + _delta]
                            else:
                                v = gauss[x, y]
#                               v = gauss[x + _delta, y]
                            rgb = colorsys.hsv_to_rgb(h, s, v)
                            r = int(rgb[0]*255.0)
                            g = int(rgb[1]*255.0)
                            b = int(rgb[2]*255.0)
                            rgbmatrix5x5.set_pixel(x, y, r, g, b)
                    rgbmatrix5x5.show()
                    end = time.time()
                    t = end - start
                    if t < 0.04:
                        time.sleep(0.04 - t)
                        pass
                if not enabled:
                    break
        self._clear(rgbmatrix5x5)
        self._log.info('blinky ended.')


    # ..........................................................................
    def _scan(self, rgbmatrix5x5):
        '''
            KITT- or Cylon-like eyeball scanning.
        '''
        global enabled
        self._log.info('starting scan...')

        r = int(255.0)
        g = int(64.0)
        b = int(0.0)
#       start = time.time()
#       for x in range(self._width):
        x = 2
        _delay = 0.25

        while enabled:
#           for i in range(count):
            for y in range(0,self._height):
                rgbmatrix5x5.clear()
                rgbmatrix5x5.set_pixel(x, y, r, g, b)
                rgbmatrix5x5.show()
                time.sleep(_delay)
            for y in range(self._height-1,0,-1):
                rgbmatrix5x5.clear()
                rgbmatrix5x5.set_pixel(x, y, r, g, b)
                rgbmatrix5x5.show()
                time.sleep(_delay)
            if not enabled:
                break
        self._clear(rgbmatrix5x5)
        self._log.debug('scan ended.')


    # ..........................................................................
    def _random(self, rgbmatrix5x5):
        '''
            Display an ever-changing random pattern.
        '''
        global enabled
        self._log.info('starting random...')
        count = 0
        while enabled:
            rand_hue = numpy.random.uniform(0.1, 0.9)
            rand_mat = numpy.random.rand(self._width,self._height)
            for y in range(self._height):
                for x in range(self._width):
#                   h = 0.1 * rand_mat[x, y]
                    h = rand_hue * rand_mat[x, y]
                    s = 0.8
                    v = rand_mat[x, y]
                    rgb = colorsys.hsv_to_rgb(h, s, v)
                    r = int(rgb[0]*255.0)
                    g = int(rgb[1]*255.0)
                    b = int(rgb[2]*255.0)
                    rgbmatrix5x5.set_pixel(x, y, r, g, b)
            if not enabled:
                break
            rgbmatrix5x5.show()
            time.sleep(0.01)
        self._clear(rgbmatrix5x5)
        self._log.info('random ended.')


    # ..........................................................................
    def set_color(self, color):
        '''
            Set the color of both RGB Matrix displays.
        '''
        self._set_color(self._rgbmatrix5x5_PORT, color)
        self._set_color(self._rgbmatrix5x5_STBD, color)


    # ..........................................................................
    def _set_color(self, rgbmatrix5x5, color):
        '''
            Set the color of the RGB Matrix.
        '''
        for y in range(self._height):
            for x in range(self._width):
                rgbmatrix5x5.set_pixel(x, y, color.red, color.green, color.blue)
        rgbmatrix5x5.show()


    # ..........................................................................
    def _clear(self, rgbmatrix5x5):
        '''
            Clears the RGB Matrix by setting its color to black.
        '''
        self._set_color(rgbmatrix5x5, Color.BLACK)


    # ..........................................................................
    def set_display_type(self, display_type):
        self._display_type = display_type


    # ..........................................................................
    def close(self):
        if self._closing:
            self._log.warning('already closing.')
            return
        self._closing = True
        self.disable()
        self._closed = True
        self._log.info('closed.')

#EOF
