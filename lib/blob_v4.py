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
# https://picamera.readthedocs.io/en/release-1.13/api_camera.html
# https://picamera.readthedocs.io/en/release-1.13/api_camera.html#picamera
# https://picamera.readthedocs.io/en/release-1.13/api_array.html
# https://picamera.readthedocs.io/en/release-1.13/_modules/picamera/array.html#PiRGBArray
#

import sys, time, math, colorsys, threading, traceback
from datetime import datetime as dt
import numpy as np
import picamera
import picamera.array
from PIL import Image
from picamera.array import PiRGBArray
from colorama import init, Fore, Style
init()

from lib.enums import Color
from lib.logger import Logger, Level
from lib.config_loader import ConfigLoader
from lib.motors_v2 import Motors
from lib.rate import Rate


import io
import time
import threading
import picamera

_lock = threading.Lock()

class ImageProcessor(threading.Thread):

    def __init__(self, config, camera, thread_num, enabled):
        super(ImageProcessor, self).__init__()
        self._camera = camera
        self._thread_num = thread_num
        self._log = Logger("proc.{}".format(thread_num), Level.INFO)
        _config = config['ros'].get('image_processor')
        self._flip_horizontal = _config.get('flip_horizontal')
        self._flip_vertical   = _config.get('flip_vertical')
        self._blob_color      = _config.get('blob_color') # [151, 55, 180] # hue = 286
        self._start_row       = _config.get('start_row') # the top row of the image to be processed
        self._end_row         = _config.get('end_row')   # the bottom row of the image to be processed
        self._take_snapshot   = _config.get('take_snapshot')
        self._print_image     = _config.get('print_image')
        self._print_summary   = _config.get('print_summary')
        self._threshold       = _config.get('filter_threshold') # low pass color filter threshold
        self._suppress_info   = _config.get('suppress_info') # if True only print peak
        # ........................
        _blob_config = config['ros'].get('blob')
        self._width           = _blob_config.get('image_width')
        self._height          = _blob_config.get('image_height')
        if self._end_row == -1:
            self._end_row = self._height - 1
        elif self._end_row >= self._height:
            raise Exception('specified end row {:d} must be less than image height {:d}',format(self._end_row, self._height))
        # ........................
        self._log.info(Fore.GREEN + Style.BRIGHT + 'camera resolution: {}'.format(self._camera.resolution))
        self._pool = None
        self._location        = -1 # last-determined location of blob
        self._output = None #PiRGBArray(camera)
        self.event = threading.Event()
        self._enabled = enabled
        self.terminated = False
        self._log.info('ready.')
        self.start()
        self._log.info('started.')

    @property
    def output(self):
        if self._output is None:
            self._output = PiRGBArray(self._camera)
        return self._output

    @property
    def thread_num(self):
        return self._thread_num

    def set_pool(self, pool):
        if not self._pool:
            self._pool = pool

    def run(self):
        # This method runs in a separate thread
        global done
        while self._enabled and not self.terminated:
            # wait for an image to be written to output
            if self.event.wait(1):
                try:
                    # read image and do some processing on it
                    self._log.info(Fore.MAGENTA + Style.BRIGHT + 'grab image from processor #{}...'.format(self._thread_num))

                    with self.output as _output:
#                       _something = self.stream.flush()
                        self._log.info(Fore.GREEN + Style.BRIGHT + 'a. output assigned: {}'.format(type(_output.array)))
#                       _image = Image.open(_output)
                        _image = Image.fromarray(_output.array)
                        self._log.info(Fore.MAGENTA + Style.BRIGHT + 'b. image created: {}'.format(type(_image)))
                        self._process_image(_image)
                        self._log.info(Fore.MAGENTA + Style.BRIGHT + 'c. processed image; output.array: {}   --------------- '.format(type(_output.array)))

                        self._output.seek(0)
                        self._output.truncate()
                        self._log.info(Fore.MAGENTA + Style.BRIGHT + 'd. output released resources: {}'.format(type(_output.array)))


                    # set done to True if you want the script to terminate at some point
                    # done=True
                finally:
                    self._log.info(Fore.MAGENTA + 'A. finally seek/truncate output from processor #{}...'.format(self._thread_num))
                    # reset output and event
                    self._stream = None
                    self.event.clear()
                    self._log.info(Fore.MAGENTA + 'B. finally seek/truncate output from processor as self.')
                    # return ourselves to the pool
                    with _lock:
                        self._log.info(Fore.MAGENTA + 'C. appending processor #{} back to pool with {} elements.'.format(self._thread_num, len(self._pool)))
                        self._pool.append(self)
                        self._log.info(Fore.MAGENTA + 'D. appended processor #{} back to pool with {} elements.'.format(self._thread_num, len(self._pool)))
                self._log.info('end run()')

    # ..........................................................................
    def _process_image(self, image):
        self._log.info(Fore.MAGENTA + 'processing image for width {:d} pixels from start {:d} to {:d} rows...'.format(self._width, self._start_row, self._end_row))
        self._start_time = dt.now()
        _column_summary = [0] * self._width
        # write image
        if self._flip_vertical: # upside down, flipped horizontally
            for _row in reversed(range(self._start_row, self._end_row + 1)):
                self._process_row(image, _row, self._flip_horizontal, _column_summary)
        else:
            for _row in range(self._start_row, self._end_row + 1):
                self._process_row(image, _row, self._flip_horizontal, _column_summary)
        self._log.info(Fore.MAGENTA + 'post-processing image...')
        # post-process image array ...............
        _peak_count, _peak = self._postprocess_image(_column_summary)
        self._log.info(Fore.CYAN + Style.BRIGHT + 'peak count: {:d}; peak @ {:d}'.format(_peak_count, _peak))
        # print location of peak .................
        if self._print_summary:
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

        self._log.info(Fore.MAGENTA + 'print summary...')
        # print summary info .....................
        _delta = dt.now() - self._start_time
        _elapsed_ms = int(_delta.total_seconds() * 1000)

        if self._print_summary:
            print (Fore.BLACK + ' {:d}ms elapsed.'.format(_elapsed_ms) + Style.RESET_ALL)
        else:
            print(Style.RESET_ALL)

        self._log.info(Fore.CYAN + 'info...') # TEMP

        if not self._suppress_info:
            if _peak_count == 1:
                self._log.info(Fore.GREEN + Style.BRIGHT + 'complete: {:d}ms elapsed.'.format(_elapsed_ms) \
                    + '; found 1 peak, returned positional value of {:d}/{:d}'.format(_peak, len(_column_summary)))
            else:
                self._log.info(Fore.GREEN + 'complete: {:d}ms elapsed.'.format(_elapsed_ms) \
                    + '; found {:d} peaks, returning positional value of {:d}/{:d}'.format(_peak_count, _peak, len(_column_summary)))
    
        self._location = _peak

        # ---------------
        # we'll just wait here until another snapshot is requested by setting _capturing True
        self._log.info(Fore.CYAN + 'going into snapshot wait loop...') # TEMP

    # ..........................................................................
    def _process_row(self, image, y, flip_horiz, colarray):
        self._log.info(Fore.MAGENTA + 'processing row for object that might be an image: {}     ++++++++++ '.format(type(image)))
        self._log.info(Fore.CYAN + 'processing row {:d}...'.format(y)) # TEMP
        if self._print_image:
            print(Fore.WHITE + '{:d}\t'.format(y) + Fore.BLACK, end='')
        if flip_horiz:
            for x in reversed(range(0,image.shape[1])):
                self._log.info(Fore.CYAN + 'a. processing pixel {:d},{:d}...'.format(y,x)) # TEMP
                _rgb = image[y,x]
                _distance = ImageProcessor.color_distance(_rgb, self._blob_color)
                if _distance <= self._threshold: # then we're close
                    colarray[x] += _distance
                if self._print_image:
                    _hilite = ImageProcessor.get_hilite(_distance)
                    print(_hilite + "▪", end='')
        else:
            for x in range(0, image.shape[1]):
                self._log.info(Fore.CYAN + 'b. processing pixel {:d},{:d}...'.format(y,x)) # TEMP
                _rgb = image[y,x]
                _distance = ImageProcessor.color_distance(_rgb, self._blob_color)
                if _distance <= self._threshold: # then we're close
                    colarray[x] += _distance
                if self._print_image:
                    _hilite = ImageProcessor.get_hilite(_distance)
                    print(_hilite + "▪", end='')
        if self._print_image:
            print(Style.RESET_ALL)


    # ..........................................................................
    def _postprocess_image(self, column_summary):
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
        _column_max = 0.0
        _peak_max = 0
        _peak_count = 0
        _colors = ImageProcessor.get_colors()
        self._peak_summary = [0] * self._width

        # get max value of all columns
        for i in range(len(column_summary)):
            _v = column_summary[i]
            _column_max = max(_column_max, _v)
        _steps = Blob.get_steps(0.0, _column_max, 10)

        _sum = sum(column_summary)
        if _sum == 0.0:
            if not self._suppress_info:
                print(Fore.CYAN + Style.BRIGHT + 'none:\t' + Style.RESET_ALL, end='')
                for i in range(len(column_summary)):
                    print(_colors[0] + "▪", end='')
                print(Style.RESET_ALL)
            else:
                self._log.info('no beacon found.')
            return 0, -1

        # get and optionally print column summaries, derive peak summary (of enumerated ints) ......
        if self._print_summary:
            print(Fore.CYAN + Style.BRIGHT + 'sum:\t' + Style.RESET_ALL, end='')
        for i in range(len(column_summary)):
            _v = column_summary[i]
            _ev = Blob.get_enum_value(_v, _steps)
            self._peak_summary[i] = _ev
            _peak_max = max(_peak_max, _ev)
            if self._print_summary:
                _hilite = _colors[_ev]
                print(_hilite + "▪", end='')
        if self._print_summary:
            print(Style.RESET_ALL)

        # obtain and optionally print column peaks .........
        _first_peak = None
        _last_peak  = None
        _peak_color = _colors[3]
        if self._print_summary:
            print(Fore.CYAN + Style.BRIGHT + 'peaks:\t' + Style.RESET_ALL, end='')
        for i in range(len(self._peak_summary)):
            _v = self._peak_summary[i]
            if _v >= _peak_max: # is a peak column
                if _first_peak is None:
                    _first_peak = i
                _last_peak = i
                _hilite = _peak_color
                _peak_count += 1
            else:
                _hilite = _colors[0]
            if self._print_summary:
                print(_hilite + "▪", end='')
        if self._print_summary:
            print(Style.RESET_ALL)

        _peak_spread = round(( _last_peak - _first_peak ) / self._width * 100.0 )
        if _peak_spread == 0: # no spread, just return the peak value
            self._log.info('no spread, just return the peak value')
            return _peak_count, _first_peak
        elif _peak_spread < 10: # spread within range, so return average between first and last peak
            _average = round((_first_peak + _last_peak) / 2.0)
            self._log.info('spread within range, return average ({:d}) between first ({:d}) and last ({:d}) peak'.format(_average, _first_peak, _last_peak))
            return _peak_count, _average
        else: # no beacon discernable
            self._log.info('no beacon discernable.')
            return _peak_count, -1

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

           See also: ImageProcessor._postprocess_image()

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
        self._width     = _config.get('image_width')
        self._height    = _config.get('image_height')
        self._config    = config
        self._motors    = motors # optional
        self._pool      = [] # pool of image processors
        self._thread    = None
        self._location  = -1
#       self._capturing = False
        self._closed    = False
        self._enabled   = False
        self._log.info('ready.')

#   # ..........................................................................
#   @property
#   def capturing(self):
#       return self._capturing

     # ..........................................................................
    def capture(self):
        if not self._enabled:
            raise Exception('not enabled.')
        self._log.info(Fore.GREEN + Style.BRIGHT + 'snapshot returning location: {}'.format(self._location))
        return self._location

    # ..........................................................................
    @property
    def outputs(self):
        while self._enabled:
            with _lock:
                if self._pool:
                    processor = self._pool.pop()
                    self._log.info(Fore.BLUE + 'outputs() 1. assigning processor #{:d}...'.format(processor.thread_num)) # TEMP
                    processor.set_pool(self._pool)
                else:
                    processor = None
            if processor:
                self._log.info(Fore.BLUE + 'outputs() 2. yielding processor #{}: {}'.format(processor.thread_num, type(processor.output))) # TEMP
#               https://stackoverflow.com/questions/231767/what-does-the-yield-keyword-do
                yield processor.output
                processor.event.set()
            else:
                self._log.info(Fore.BLUE + 'outputs() 3. waiting for processor...')
                # when the pool is starved, wait a while for it to refill
                time.sleep(0.1)
 
    # ..........................................................................
    def _loop(self, _enabled):
        self._log.info(Fore.RED + 'start _loop...') # TEMP

        _rate = Rate(1) # 1Hz
        _thread_count = 4

        try:
            # summarise elements on a column basis .........
            self._log.info('starting image capture...')

            with picamera.PiCamera() as camera:
                camera.resolution = (self._width, self._height)
                camera.iso = 800
                camera.exposure_mode = 'auto'
                camera.framerate = 15
#               https://picamera.readthedocs.io/en/release-1.13/_modules/picamera/array.html#PiRGBArray
                camera.start_preview()
    #           time.sleep(2)
                self._log.info(Style.BRIGHT + '1. creating processor pool...')
                self._pool = [ImageProcessor(self._config, camera, i, _enabled) for i in range(_thread_count)]
                self._log.info(Style.BRIGHT + '2. calling camera.capture_continuous...')
#               size = ( self._width, self._height )
#               camera.capture_continuous(self.outputs, format='rgb', resize=size, use_video_port=True)
#               camera.capture_sequence(self.outputs, format='rgb', resize=size, use_video_port=True)
#               camera.capture_sequence(self.outputs, format='rgb', use_video_port=True)
                camera.capture_sequence(self.outputs, format='rgb', use_video_port=True)
                self._log.info(Style.BRIGHT + '3. called camera.capture_continuous...')
                time.sleep(3)
                _rate.wait()
            
#           self._close_pool()
            self._log.info('end _loop.') # TEMP

        except picamera.PiCameraMMALError:
            self._log.error('could not get camera: in use by another process.')
        except Exception as e:
            self._log.error('error in blob loop: {}'.format(e))
            self._log.error('traceback in blob loop: {}'.format(traceback.format_exc()))
        finally:
            self._log.set_suppress(False)
            self._motors.set_led_show_battery(True)
            self._log.info('finis.')

    # ..........................................................................
    def _close_pool(self):
        self._log.info(Fore.RED + 'closing pool...') # TEMP
        # Shut down the processors in an orderly fashion
        try:
            while self._pool:
                self._log.info(Fore.RED + 'pool _loop.') # TEMP
                with _lock:
                    self._log.info(Fore.RED + 'get processor.') # TEMP
                    processor = self._pool.pop()
                    if processor is not None:
                        processor.terminated = True
                        processor.join()
                        self._log.info(Fore.RED + 'processor joined.') # TEMP
        except Exception:
            self._log.error('error closing processor pool: {}'.format(traceback.format_exc()))
        self._log.info(Fore.RED + 'pool closed.') # TEMP

#    # ..........................................................................
#    def old_loop(self, _enabled, _capturing):
#        '''
#           Captures an image, optionally writing it to the console in color,
#           then post-processing the array to enumerate the peak of matches
#           in a single linear array.
#           We don't necessarily process the whole image (it takes a long time),
#           processing from start_row to end_row only.
#        '''
#        self._start_time = dt.now()
#        self._column_summary = [0] * self._width
#        try:
#            # summarise elements on a column basis .........
#            self._motors.set_led_show_battery(False)
#            self._motors.set_led_color(Color.BLACK)
#            self._log.debug('starting image capture...')
#            with picamera.PiCamera() as camera:
#                with CaptureArray(camera, Level.INFO) as output:
#                with PiRGBArray(camera) as output:
#                    camera.resolution = (self._width, self._height)
#                    camera.iso = 800
#                    camera.exposure_mode = 'auto'
##                   time.sleep(1.0)
#                    if self._take_snapshot: # take JPEG image and save to file
#                        _ts = dt.utcfromtimestamp(dt.utcnow().timestamp()).isoformat().replace(':','_').replace('-','_').replace('.','_')
#                        _filename = './snapshot-{}.jpg'.format(_ts)
#                        self._log.info('writing snapshot to file: {}'.format(_filename))
#                        camera.capture(_filename)
##                       output.truncate(0)
#
#                    _rate = Rate(5) # 10Hz
#                    while _enabled:
#
#                        self._log.info(Fore.GREEN + Style.BRIGHT + 'looping snapshot...')
#                        # capture an image
##                       camera.capture(output, 'rgb')
#                        _use_video_port = False
#                        for x in camera.capture_continuous(output, format='rgb', use_video_port=_use_video_port):
#
#                            image = output.array
#                            if image is not None:
#                                self._log.info('captured size {:d}x{:d} image.'.format(image.shape[1], image.shape[0]))
#                            else:
#                                self._log.info('captured no image.')
#
#                            output.truncate(0)
##                           self._process_image(image)
##                           self._log.set_suppress(True)
#
##                           while not _capturing:
##                               self._log.info(Fore.MAGENTA + Style.DIM + 'waiting...')
#                            time.sleep(0.5)
##                               _rate.wait()
##                           _capturing = False
##                           self._log.info(Fore.CYAN + Style.DIM + 'loop end, repeating...')
#
#
#        except picamera.PiCameraMMALError:
#            self._log.error('could not get camera: in use by another process.')
#        except Exception:
#            self._log.error('error starting ros: {}'.format(traceback.format_exc()))
#        finally:
#            self._log.info('finis.')


    # ..........................................................................
    @property
    def enabled(self):
        return self._enabled

    # ..........................................................................
    def enable(self):
        if not self._closed:
            self._enabled = True
            # if we haven't started the thread yet, do so now...
            if self._thread is None:
                try:
                    self._motors.set_led_show_battery(False)
                    self._motors.set_led_color(Color.BLACK)
#                   self._thread = threading.Thread(target=Blob._loop, args=[self, lambda: self.enabled, lambda: self.capturing ])
                    self._thread = threading.Thread(target=Blob._loop, args=[self, lambda: self.enabled])
                    self._thread.start()
                    self._log.info('blob loop enabled.')
                finally:
                    self._log.set_suppress(False)
                    self._motors.set_led_show_battery(True)
            else:
                self._log.warning('cannot enable blob loop: thread already exists.')
        else:
            self._log.warning('cannot enable blob loop: already closed.')

    # ..........................................................................
    def disable(self):
        if self._enabled:
            self._enabled = False
            time.sleep(0.06) # just a bit more than 1 loop in 20Hz
            if self._thread is not None:
                self._thread.join(timeout=1.0)
                self._log.info('blob thread joined.')
                self._thread = None
            self._log.info('blob loop disabled.')

    # ..........................................................................
    def close(self):
        if not self._closed:
            if self._enabled:
                self.disable()
            time.sleep(0.3)
            self._close_pool()
            self._closed = True
            self._log.info('closed.')

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
