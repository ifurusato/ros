#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# Copyright 2020 by Murray Altheim. All rights reserved. This file is part of
# the Robot Operating System project and is released under the "Apache Licence,
# Version 2.0". Please see the LICENSE file included as part of this package.
#
# author:   Murray Altheim
# created:  2020-05-19
# modified: 2020-05-19
#
# see:      https://robots.org.nz/2020/05/19/four-corners/
#
# This script is used as a possible solution for the Four Corners Competition,
# as a way for a robot to locate the trajectory to a distant target. IN this
# case we're using a beacon made with a pink LED, a color that doesn't show
# up much in nature.
#

import sys, time, math, colorsys, traceback
from datetime import datetime as dt
import numpy as np
import picamera
import picamera.array
from picamera.array import PiRGBArray
from colorama import init, Fore, Style
init()

from lib.enums import Color
from lib.logger import Logger, Level
from lib.config_loader import ConfigLoader
from lib.motors_v2 import Motors

# ..............................................................................
class Blob(object):

    def __init__(self, config, motors, level):
        '''
           A poor-man's blob sensor, using a standard Raspberry Pi camera and
           a beacon made from a pink LED. We derive the target color from a
           JPEG image taken directly from the camera. The color is set via
           configuration, so this could be changed to say, an orange hue if
           the target was a flourescent orange can.

           Configuration includes ability to flip horizontally or vertically;
           the image size (which the Pi camera will round up and note if you
           choose an oddball size); the start and end row to capture.
           The logs will be suppressed and the ThunderBorg motor controller
           LED is dimmed during the capture, in order to avoid logging during
           image capture and to eliminate reflections.

           See also: postprocess_image()

           :param config: application configuration
           :param motors: optional access to the motor controller to turn
                          off its power indicator LED, which may interfere
                          with the camera image
           :param leve:   the log level
        '''
        self._log = Logger("blob", level)
        if config is None:
            raise ValueError('no configuration provided.')
        _config = config['ros'].get('blob')
        self._motors          = motors # optional
        self._blob_color      = _config.get('blob_color') # [151, 55, 180] # hue = 286
        self._flip_horizontal = _config.get('flip_horizontal')
        self._flip_vertical   = _config.get('flip_vertical')
        self._width           = _config.get('image_width')
        self._height          = _config.get('image_height')
        self._start_row       = _config.get('start_row') # the top row of the image to be processed
        self._end_row         = _config.get('end_row')   # the bottom row of the image to be processed
        self._threshold       = _config.get('filter_threshold') # low pass color filter threshold
        if self._end_row == -1:
            self._end_row = self._height - 1
        elif self._end_row >= self._height:
            raise Exception('specified end row {:d} must be less than image height {:d}',format(self._end_row, self._height))
        self._log.info('ready.')

    # ..........................................................................
    def capture(self):
        '''
           Captures an image, optionally writing it to the console in color,
           then post-processing the array to enumerate the peak of matches
           in a single linear array.
           We don't necessarily process the whole image (it takes a long time),
           processing from start_row to end_row only.
        '''
        self._start_time = dt.now()
        self._column_summary = [0] * self._width
        try:
            # summarise elements on a column basis .........
            self._motors.set_led_show_battery(False)
            self._motors.set_led_color(Color.BLACK)
            self._log.debug('starting image capture...')
            with picamera.PiCamera() as camera:
                with PiRGBArray(camera) as output:
                    camera.resolution = (self._width, self._height)
                    camera.iso = 800
                    camera.exposure_mode = 'auto'
#                   time.sleep(1.0)
                    camera.capture(output, 'rgb')
                    image = output.array
                    _width = image.shape[1]
                    _height = image.shape[0]
                    self._log.debug('captured size {:d}x{:d} image.'.format(_width, _height))
                    self._log.set_suppress(True)
                    # write image
                    for _row in range(self._start_row + 1, self._end_row + 1):
                        self.process_row(image, _row, self._column_summary)

        except picamera.PiCameraMMALError:
            self._log.error('could not get camera: in use by another process.')
        except Exception:
            self._log.error('error starting ros: {}'.format(traceback.format_exc()))
        finally:
            self._log.set_suppress(False)
            self._motors.set_led_show_battery(True)

        # post-process image array ...............
        _peak = self.postprocess_image()

        # print location of peak .................
        print(Fore.CYAN + Style.BRIGHT + 'peak:\t' + Style.RESET_ALL, end='')
        _halfway = round(len(self._peak_summary) / 2)
        for i in range(len(self._peak_summary)):
            if i == _halfway:
                _hilite = Fore.MAGENTA if i == _peak else Fore.CYAN
            elif i == _peak:
                _hilite = Fore.RED
            else:
                _hilite = Fore.BLACK + Style.DIM
            print(_hilite + "▪", end='')

        # print summary info .....................
        _delta = dt.now() - self._start_time
        _elapsed_ms = int(_delta.total_seconds() * 1000)
        print (Fore.BLACK + ' {:d}ms elapsed.'.format(_elapsed_ms) + Style.RESET_ALL)

    # ..........................................................................
    def postprocess_image(self):
        '''
           This applies a low pass color filter to all elements in a given column,
           then derives a summary of the peak values of the column so that an
           enumerated distribution with a minimum acceptance threshold acts as
           a second filter, generating the resulting single row array which
           represents those columns with the highest matches for the target color.

           Get the maximum value for any column, then distribute from 0 to that
           value to get the set of enumeration thresholds. Then colorise each
           array element according to its place in that enumeration.

           1. If there is only a single array element representing a peak value,
              we have found the beacon.

           2. If the span between the left-most and right-most peaks of that
              array are less than a fixed percentage (e.g., 10%) of the image
              width, we assume the matches are looking at the same object, so
              we average between the range and assume that center value is the
              location of the beacon, returning that value.

           3. If no peaks are registered or the spread is too great, we assume
              either the beacon isn't visible in the image or the image is too
              confusing to locate the beacon, so we act as if it is not visible.

           This returns a single value, being the position in the column array
           where we think the beacon is located. Since arrays are zero-indexed,
           a -1 is returned if we haven't found the beacon.
        '''
        if sum(self._column_summary) == 0.0:
            print(Fore.CYAN + Style.BRIGHT + 'none:\t' + Style.RESET_ALL, end='')
            for i in range(len(self._column_summary)):
                print(_colors[0] + "▪", end='')
            print(Style.RESET_ALL)
            return -1

        _column_max = 0.0
        _peak_max = 0
        _colors = Blob.get_colors()
        self._peak_summary = [0] * self._width

        # get max value of all columns
        for i in range(len(self._column_summary)):
            _v = self._column_summary[i]
            _column_max = max(_column_max, _v)
        _steps = Blob.get_steps(0.0, _column_max, 10)

        # get and optionally print column summaries, derive peak summary (of enumerated ints) ......
        for i in range(len(self._column_summary)):
            _v = self._column_summary[i]
            _ev = Blob.get_enum_value(_v, _steps)
            self._peak_summary[i] = _ev
            _peak_max = max(_peak_max, _ev)

        # obtain and optionally print column peaks .........
        _first_peak = None
        _last_peak  = None
        _peak_color = _colors[3]
        for i in range(len(self._peak_summary)):
            _v = self._peak_summary[i]
            if _v >= _peak_max: # is a peak column
                if _first_peak is None:
                    _first_peak = i
                _last_peak = i
                _hilite = _peak_color
            else:
                _hilite = _colors[0]

        _peak_spread = round(( _last_peak - _first_peak ) / self._width * 100.0 )
        if _peak_spread == 0: # no spread, just return the peak value
            return _first_peak
        elif _peak_spread < 10: # spread within range, so return average (mid-point) between first and last peak
            _average = round((_first_peak + _last_peak) / 2.0)
            return _average
        else: # no beacon discernable
            return -1

    # ..........................................................................
    @staticmethod
    def get_colors():
        colors = []
        colors.append(Fore.BLACK + Style.DIM)
        colors.append(Fore.BLACK + Style.NORMAL)
        colors.append(Fore.BLUE + Style.NORMAL)
        colors.append(Fore.BLUE + Style.BRIGHT)
        colors.append(Fore.CYAN + Style.NORMAL)
        colors.append(Fore.GREEN + Style.NORMAL)
        colors.append(Fore.GREEN + Style.BRIGHT)
        colors.append(Fore.YELLOW + Style.NORMAL)
        colors.append(Fore.YELLOW + Style.BRIGHT)
        colors.append(Fore.RED + Style.NORMAL)
        colors.append(Fore.RED + Style.BRIGHT)
        colors.append(Fore.MAGENTA + Style.NORMAL)
        colors.append(Fore.MAGENTA + Style.BRIGHT)
        return colors

    # ..........................................................................
    @staticmethod
    def get_enum_value(value, steps):
        for i in range(len(steps)):
            _step = steps[i]
            if value < _step:
                return i - 1
        return 0

    # ..........................................................................
    @staticmethod
    def get_steps(start, end, n):
        '''
           Enumerates the values between start and end, returning an
           array of floats.
        '''
        if start == 0.0 == end:
            return [0.0] * n
        step = (end-start)/float(n-1)
        return np.arange(start, end, step)

    # ..........................................................................
    def set_lights(self, enable):
        if self._motors:
            if enable:
                self._motors.set_led_show_battery(True)
            else:
                self._motors.set_led_show_battery(False)
                self._motors.set_led_color(Color.BLACK)

    # ..........................................................................
    def process_row(self, image, y, colarray):
        for x in reversed(range(0,image.shape[1])):
            _rgb = image[y,x]
            _distance = Blob.color_distance(_rgb, self._blob_color)
            if _distance <= self._threshold: # then we're close
                colarray[x] += _distance

    # ..........................................................................
    @staticmethod
    def color_distance(e0, e1):
        hsv0 = colorsys.rgb_to_hsv(e0[0], e0[1], e0[2])
        hsv1 = colorsys.rgb_to_hsv(e1[0], e1[1], e1[2])
        dh = min(abs(hsv1[0]-hsv0[0]), 360-abs(hsv1[0]-hsv0[0])) / 180.0
        ds = abs(hsv1[1]-hsv0[1])
        dv = abs(hsv1[2]-hsv0[2]) / 255.0
        distance = math.sqrt(dh*dh+ds*ds+dv*dv)
        return distance

    # ..........................................................................
    @staticmethod
    def get_hilite(dist):
        if  dist < 0.025:
            return Fore.MAGENTA + Style.BRIGHT
        elif dist < 0.05:
            return Fore.MAGENTA + Style.NORMAL
        elif dist < 0.08:
            return Fore.RED + Style.BRIGHT
        elif dist < 0.10:
            return Fore.RED + Style.NORMAL
        elif dist < 0.15:
            return Fore.YELLOW + Style.BRIGHT
        elif dist < 0.2:
            return Fore.YELLOW + Style.NORMAL
        elif dist < 0.3:
            return Fore.GREEN + Style.BRIGHT
        elif dist < 0.4:
            return Fore.GREEN + Style.NORMAL
        elif dist < 0.5:
            return Fore.CYAN + Style.NORMAL
        elif dist < 0.6:
            return Fore.BLUE + Style.BRIGHT
        elif dist < 0.7:
            return Fore.BLUE + Style.NORMAL
        elif dist < 0.8:
            return Fore.BLACK + Style.NORMAL
        else:
            return Fore.BLACK + Style.DIM

## main .........................................................................
#def main(argv):
#
#    try:
#
#        # read YAML configuration
#        _level = Level.INFO
#        _loader = ConfigLoader(_level)
#        filename = 'config.yaml'
#        _config = _loader.configure(filename)
#
#        _ros = Blob(_config, _level)
#        _ros.capture()
#
#    except Exception:
#        print(Fore.RED + Style.BRIGHT + 'error starting ros: {}'.format(traceback.format_exc()) + Style.RESET_ALL)
#
## call main ....................................................................
#if __name__== "__main__":
#    main(sys.argv[1:])

#EOF
