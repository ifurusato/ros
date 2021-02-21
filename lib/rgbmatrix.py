#!/usr/bin/env python3

import sys, time, colorsys
from threading import Thread
from enum import Enum
from colorama import init, Fore, Style
init()

try:
    import numpy
except ImportError:
    sys.exit("This script requires the numpy module\nInstall with: pip3 install --user numpy")
try:
    import psutil
except ImportError:
    sys.exit("This script requires the psutil module\nInstall with: pip3 install --user psutil")

from lib.logger import Level, Logger
from lib.feature import Feature
from lib.enums import Color, Orientation
from rgbmatrix5x5 import RGBMatrix5x5

# ..............................................................................
class DisplayType(Enum):
    BLINKY  = 1
    CPU     = 2
    DARK    = 3
    RAINBOW = 4
    RANDOM  = 5
    SCAN    = 6
    SWORL   = 7
    SOLID   = 8

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
        self._log.info('rgbmatrix width,height: {},{}'.format(self._width, self._height))
        self._thread_PORT = None
        self._thread_STBD = None
        self._color = Color.RED # used by _solid
        enabled = False
        self._closing = False
        self._closed = False
        self._display_type = DisplayType.DARK # default
        # used by _cpu:
        self._max_value = 0.0 # TEMP
        self._buf = numpy.zeros((self._rgbmatrix5x5_STBD._width, self._rgbmatrix5x5_STBD._height))
        self._colors = [ Color.GREEN, Color.YELLOW_GREEN, Color.YELLOW, Color.ORANGE, Color.RED ]
        self._log.info('ready.')

    # ..........................................................................
    def name(self):
        return 'RgbMatrix'

    # ..........................................................................
    def _get_target(self):
        if self._display_type is DisplayType.BLINKY:
            return RgbMatrix._blinky
        elif self._display_type is DisplayType.CPU:
            return RgbMatrix._cpu
        elif self._display_type is DisplayType.DARK:
            return RgbMatrix._dark
        elif self._display_type is DisplayType.RAINBOW:
            return RgbMatrix._rainbow
        elif self._display_type is DisplayType.RANDOM:
            return RgbMatrix._random
        elif self._display_type is DisplayType.SCAN:
            return RgbMatrix._scan
        elif self._display_type is DisplayType.SOLID:
            return RgbMatrix._solid
        elif self._display_type is DisplayType.SWORL:
            return RgbMatrix._sworl

    # ..........................................................................
    def enable(self):
        global enabled
        if not self._closed and not self._closing:
            if self._thread_PORT is None and self._thread_STBD is None:
                enabled = True
                self._thread_PORT = Thread(name='rgb-port', target=self._get_target(), args=[self, self._rgbmatrix5x5_PORT])
                self._thread_STBD = Thread(name='rgb-stbd', target=self._get_target(), args=[self, self._rgbmatrix5x5_STBD])
                self._thread_PORT.start()
                self._thread_STBD.start()
                self._log.debug('enabled.')
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
        self._log.debug('disabling...')
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
        self._log.debug('disabled.')

    # ..........................................................................
    def _cpu(self, rgbmatrix5x5):
        '''
            A port of the CPU example from the Matrix 11x7. 

            For some reasoon the output needs to be rotated 90 degrees to work properly.
        '''
        self._log.info('starting cpu...')
        i = 0
        cpu_values = [0] * self._width
        while enabled:
            try:
                cpu_values.pop(0)
                cpu_values.append(psutil.cpu_percent())

#               # display cpu_values and max (turns out to be 50.0)
#               for i in range(0, len(cpu_values)-1):
#                   self._max_value = max(self._max_value, cpu_values[i])
#               self._log.info(Fore.BLUE + 'cpu_values: {}, {}, {}, {}, {}; '.format(cpu_values[0], cpu_values[1], cpu_values[2], cpu_values[3], cpu_values[4]) \
#                       + Style.BRIGHT + '\tmax: {:5.2f}'.format(self._max_value))

                self._set_graph(rgbmatrix5x5, cpu_values, low=0.0, high=50.0) # high was 25
                rgbmatrix5x5.show()
                time.sleep(0.2)
            except KeyboardInterrupt:
                self._clear(rgbmatrix5x5)
                self._log.info('cpu ended.')
                sys.exit(0)

    # ......................................................
    def _set_graph(self, rgbmatrix5x5, values, low=None, high=None, x=0, y=0):
        '''
            Plot a series of values into the display buffer. 
        '''
        global enabled
        # def set_graph(self, values, low=None, high=None, brightness=1.0, x=0, y=0, width=None, height=None):
#       x=0 
#       y=0
        _width = self._width - 1
        _height = self._height + 0
        if low is None:
            low = min(values)
        if high is None:
            high = max(values)
        self._buf = self._grow_buffer(x + _width, y + _height)
        span = high - low
        for p_y in range(0, _height):
            try:
                _value = values[p_y] 
                _value -= low
                _value /= float(span)
                _value *= _width * 10.0
                _value = min(_value, _height * 12.0)
                _value = max(_value, 0.0)

                if _value > 5.0:
                    _value = 50.0

#               self._log.info(Fore.MAGENTA + 'p_y={}; _value: {}'.format(p_y, _value) + Style.RESET_ALL)
                for p_x in range(0, _width):
                    _r = self._colors[p_x].red
                    _g = self._colors[p_x].green
                    _b = self._colors[p_x].blue
                    if _value <= 10.0:
                        _r = (_value / 10.0) * _r
                        _g = (_value / 10.0) * _g
                        _b = (_value / 10.0) * _b
                    _x = x + (_width - p_x)
                    _y = y + p_y
                    self._log.info(Fore.YELLOW + 'setting pixel x={}/{}, y={}/{};'.format(_x, _width, _y, _height) + Fore.MAGENTA + '\tvalue: {:>5.2f}'.format(_value) + Style.RESET_ALL)
                    rgbmatrix5x5.set_pixel(_x, _y , _r, _g, _b)
                    _value -= 10.0
                    if _value < 0.0:
                        _value = 0.0
                print('')
            except IndexError:
                return

    # ......................................................
    def _grow_buffer(self, x, y):
        '''
            Grows a copy of the buffer until the new shape fits inside it.
            :param x: Minimum x size
            :param y: Minimum y size
        '''
        x_pad = max(0, x - self._buf.shape[0])
        y_pad = max(0, y - self._buf.shape[1])
        return numpy.pad(self._buf, ((0, x_pad), (0, y_pad)), 'constant')

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
    def _sworl(self, rgbmatrix5x5):
        '''
            Display a sworl pattern, whatever that is.
        '''
        global enabled
        self._log.info('starting sworl...')

        try:
            for r in range(0, 10, 1):
                rgbmatrix5x5.set_all(r, 0, 0)
                rgbmatrix5x5.show()
                time.sleep(0.003)
            for i in range(0, 5):
                for r in range(10, 250, 10):
                    _blue = r - 128 if r > 128 else 0 
                    rgbmatrix5x5.set_all(r, _blue, 0)
                    rgbmatrix5x5.show()
                    time.sleep(0.01)
                if not enabled:
                    break;
                for r in range(250, 10, -10):
                    _blue = r - 128 if r > 128 else 0 
                    rgbmatrix5x5.set_all(r, _blue, 0)
                    rgbmatrix5x5.show()
                    time.sleep(0.01)
                if not enabled:
                    break;
            self._log.info('sworl ended.')
        except KeyboardInterrupt:
            self._log.info('sworl interrupted.')
        finally:
            self.set_color(Color.BLACK)

    # ..........................................................................
    def set_solid_color(self, color):
        self._color = color

    # ..........................................................................
    def show_color(self, color, orientation):
        self.set_solid_color(color)
        if orientation is Orientation.PORT:
            self._set_color(self._rgbmatrix5x5_PORT, self._color)
        else:
            self._set_color(self._rgbmatrix5x5_STBD, self._color)

    # ..........................................................................
    def show_hue(self, hue, orientation):
        '''
        Set the color of the display to the hue specified as a value from 0.0 - 1.0.

        Not sure this works, abandoned for now.
        '''
        rgb = colorsys.hsv_to_rgb(abs(hue), 1.0, 1.0)
        r = int(rgb[0]*255.0)
        g = int(rgb[1]*255.0)
        b = int(rgb[2]*255.0)
        if orientation is Orientation.PORT or orientation is Orientation.BOTH:
            self._rgbmatrix5x5_PORT.set_all(r, g, b)
            self._rgbmatrix5x5_PORT.show()
        if orientation is Orientation.STBD or orientation is Orientation.BOTH:
            self._rgbmatrix5x5_STBD.set_all(r, g, b)
            self._rgbmatrix5x5_STBD.show()

    # ..........................................................................
    def _solid(self, rgbmatrix5x5):
        '''
            Display a specified static, solid color on only the port display.
        '''
        global enabled
#       self.set_color(self._color)
#       self._set_color(self._rgbmatrix5x5_STBD, self._color)
        self._set_color(self._rgbmatrix5x5_PORT, self._color)
        self._log.info('starting solid color to {}...'.format(str.lower(self._color.name)))
        while enabled:
            time.sleep(0.2)

    # ..........................................................................
    def _solid(self, rgbmatrix5x5):
        '''
            Display a specified static, solid color on only the port display.
        '''
        global enabled
#       self.set_color(self._color)
#       self._set_color(self._rgbmatrix5x5_STBD, self._color)
        self._set_color(self._rgbmatrix5x5_PORT, self._color)
        self._log.info('starting solid color to {}...'.format(str.lower(self._color.name)))
        while enabled:
            time.sleep(0.2)

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
        rgbmatrix5x5.set_all(color.red, color.green, color.blue)
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
        self.set_color(Color.BLACK)
        self._closing = True
        self.disable()
        self._closed = True
        self._log.info('closed.')

#EOF
