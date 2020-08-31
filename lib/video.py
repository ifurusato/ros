#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# Copyright 2020 by Murray Altheim. All rights reserved. This file is part of
# the Robot Operating System project and is released under the "Apache Licence,
# Version 2.0". Please see the LICENSE file included as part of this package.
#
# author:   Murray Altheim
# created:  2019-12-23
# modified: 2020-03-12
#
# Once running, access the video stream from:    http://pi-address:8001/
#
# source: https://picamera.readthedocs.io/en/release-1.13/recipes2.html#web-streaming
#

import os, sys, time, tzlocal, threading, traceback, io, socket, socketserver, itertools, logging, ffmpeg, picamera
from pathlib import Path
from picamera import Color
from datetime import datetime as dt
from threading import Condition
from http import server
from colorama import init, Fore, Style
init()

from lib.enums import Orientation
from lib.logger import Level, Logger
from lib.matrix import Matrix

VIDEO_WIDTH  = 640
VIDEO_HEIGHT = 480

# ..............................................................................
class OutputSplitter(object):
    '''
        An output (as far as picamera is concerned), is just a filename or an object
        which implements a write() method (and optionally the flush() and close() methods)
    '''
    def __init__(self, filename):
        self.frame = None
        self.buffer = io.BytesIO()
        self._log = Logger('output', Level.INFO)
        self.output_file = io.open(filename, 'wb')
        self._filename = filename
        self._log.info(Fore.MAGENTA + 'output file: {}'.format(filename))
        self._condition = Condition()
        self._log.info('ready.')

    def get_filename(self):
        return self._filename

    def write(self, buf):
        if buf.startswith(b'\xff\xd8'):
            # new frame, copy existing buffer's content and notify all clients it's available
            self.buffer.truncate()
            with self._condition:
                self.frame = self.buffer.getvalue()
                self._condition.notify_all()
            self.buffer.seek(0)
        if not self.output_file.closed:
            self.output_file.write(buf)
        return self.buffer.write(buf)

    def flush(self):
        self._log.debug('flush')
        if not self.output_file.closed:
            self.output_file.flush()
        if not self.buffer.closed:
            self.buffer.flush()

    def close(self):
        self._log.info('close')
        if not self.output_file.closed:
            self.output_file.close()
        if not self.buffer.closed:
            self.buffer.close()


# ..............................................................................
class StreamingHandler(server.BaseHTTPRequestHandler):

    def __init__(self, socket, tup, server):
        super().__init__(socket, tup, server)

    def get_page(self):
        global video_width, video_height
        return """<!DOCTYPE html>
<html>
<head>
<title>KR01 eyeball</title>
<style>
  body {{ margin: 1em }}
</style>
</head>
<body bgcolor='black'>
<img src="stream.mjpg" width="{width_value}" height="{height_value}" />
</body>
</html>
""".format(width_value=video_width, height_value=video_height)

    def do_GET(self):
        global output
        _output = output
        if self.path == '/':
            self.send_response(301)
            self.send_header('Location', '/index.html')
            self.end_headers()
        elif self.path == '/index.html':
            content = self.get_page().encode('utf-8')
            self.send_response(200)
            self.send_header('Content-Type', 'text/html')
            self.send_header('Content-Length', len(content))
            self.end_headers()
            self.wfile.write(content)
        elif self.path == '/stream.mjpg':
            self.send_response(200)
            self.send_header('Age', 0)
            self.send_header('Cache-Control', 'no-cache, private')
            self.send_header('Pragma', 'no-cache')
            self.send_header('Content-Type', 'multipart/x-mixed-replace; boundary=FRAME')
            self.end_headers()
            try:
                while True:
                    with _output._condition:
                        _output._condition.wait()
                        frame = _output.frame
                    self.wfile.write(b'--FRAME\r\n')
                    self.send_header('Content-Type', 'image/jpeg')
                    self.send_header('Content-Length', len(frame))
                    self.end_headers()
                    self.wfile.write(frame)
                    self.wfile.write(b'\r\n')
            except Exception as e:
                logging.warning('removed streaming client %s: %s', self.client_address, str(e))
        else:
            self.send_error(404)
            self.end_headers()


# ..............................................................................
class StreamingServer(socketserver.ThreadingMixIn, server.HTTPServer):
    allow_reuse_address = True
    daemon_threads = True

    def __init__(self, address, streaming_handler, f_is_enabled):
        super().__init__(address, streaming_handler)
        self._log = Logger('server', Level.INFO)
        self._enabled_flag = f_is_enabled
        self._log.info('ready.')


    def serve_forever(self):
        '''
            Handle one request at a time until the enabled flag is False.
        '''
        while self._enabled_flag():
            self._log.info('serve_forever handling request...')
            self.handle_request()

        self._log.info('exited serve_forever loop.')


# ..............................................................................
class Video():
    def __init__(self, config, lux, matrix11x7_available, level):
        super().__init__()
        global video_width, video_height, annotation_title
        self._log = Logger('video', level)
        if config is None:
            raise ValueError("no configuration provided.")
        self._config = config
        self._lux = lux
        _config = self._config['ros'].get('video')
        self._enable_streaming = _config.get('enable_streaming')
        self._port        = _config.get('port')
        self._lux_threshold = _config.get('lux_threshold')
        self._counter = itertools.count()

        # camera configuration
        self._ctrl_lights = _config.get('ctrl_lights')
        self._width       = _config.get('width')
        self._height      = _config.get('height')
        self._resolution  = ( self._width, self._height )
        self._framerate   = _config.get('framerate')
        self._convert_mp4 = _config.get('convert_mp4')
        self._remove_h264 = _config.get('remove_h264')
        self._quality     = _config.get('quality')
        self._annotate    = _config.get('annotate')
        self._title       = _config.get('title')
        self._basename    = _config.get('basename')
        self._dirname     = _config.get('dirname')
        # set globals
        video_width       = self._width
        video_height      = self._height
        annotation_title  = self._title
        self._filename = None
        self._thread   = None
        self._killer   = None
       
        # lighting configuration
        if matrix11x7_available and self._ctrl_lights:
            self._port_light = Matrix(Orientation.PORT, Level.INFO)
            self._stbd_light = Matrix(Orientation.STBD, Level.INFO)
            self._log.info('camera lighting available.')
        else:
            self._port_light = None
            self._stbd_light = None
            self._log.info('no camera lighting available.')

        if self._enable_streaming:
            self._log.info('ready: streaming on port {:d}'.format(self._port))
        else:
            self._log.info('ready: save to file only, no streaming.')

    # ..........................................................................
    def set_compass(self, compass):
        global g_compass
        g_compass = compass # used by annotation
        self._compass = compass

    # ..........................................................................
    @staticmethod
    def get_annotation():
        global annotation_title, g_compass
        _heading = g_compass.get_heading_message() if g_compass is not None else ''
        return '{} {} {}'.format(annotation_title, dt.now(tzlocal.get_localzone()).strftime('%Y-%m-%d %H:%M:%S %Z'), _heading)

    # ..........................................................................
    def is_night_mode(self):
        if self._lux is None:
            return False
        _value = self._lux.get_value()
        _threshold =  self._lux_threshold
        self._log.debug('lux: {:>5.2f} <  threshold: {:>5.2f}?'.format(_value, _threshold))
        return _value < _threshold

    # ..........................................................................
    def _get_timestamp(self):
        return dt.utcfromtimestamp(dt.utcnow().timestamp()).isoformat().replace(':','_').replace('-','_').replace('.','_')

    # ..........................................................................
    def get_filename(self):
        return self._filename

    # ..........................................................................
    def _start(self, output_splitter, f_is_enabled):
        global output # necessary for access from StreamingHandler, passed as type
        output = output_splitter
        self._output = output_splitter
        self._filename = output_splitter.get_filename()
        if self._enable_streaming:
            self._log.info('starting video with capture to file: {}'.format(output_splitter.get_filename()))
        else:
            self._log.info('starting capture to file: {}'.format(output_splitter.get_filename()))
        with picamera.PiCamera(resolution=self._resolution, framerate=self._framerate) as camera:
            self._log.info('camera framerate: {}'.format(camera.framerate))
            self._log.info('camera ISO: {}'.format(camera.iso))
            self._log.info('camera mode: {}'.format(camera.exposure_mode))
            self._log.info('camera shutter speed: {}'.format(camera.shutter_speed))
            if self._annotate:
                camera.annotate_text_size = 12
                self.set_night_mode(camera, self.is_night_mode())
#               camera.annotate_text = Video.get_annotation() # initial text
                # start video annotation thread
                self._annot = threading.Thread(target=Video._annotate, args=[self, camera, f_is_enabled ])
                self._annot.setDaemon(True)
                self._annot.start()
            if self._quality > 0:
                # values 1 (highest quality) to 40 (lowest quality), with typical values between 20 and 25
                self._log.info('camera quality: {}'.format(self._quality))
                camera.start_recording(output_splitter, format='mjpeg', quality=self._quality)
            else:
                camera.start_recording(output_splitter, format='mjpeg')

            try:
                if self._enable_streaming:
                    self._log.info('starting streaming server...')
                    address = ('', self._port)
                    server = StreamingServer(address, StreamingHandler, f_is_enabled)
                    self._killer = lambda: self.close(camera, output_splitter)
                    server.serve_forever()
                else: # keepalive
                    while f_is_enabled():
                        self._log.debug('keep-alive...')
                        time.sleep(1.0)
                self._log.info(Fore.RED + 'EXITED LOOP.                   zzzzzzzzzzzzzzzzzzzzzzzzzzzzzz ')
            except Exception:
                self._log.error('error streaming video: {}'.format(traceback.format_exc()))
            finally:
                self._log.info(Fore.RED + 'finally.')
                self.close(camera, server, output_splitter)
        self._log.info('_start: complete.')

    # ..........................................................................
    def _annotate(self, camera, f_is_enabled):
        '''
            Update the video annotation every second.
        '''
        self._camera = camera
        _count = 0
        while f_is_enabled():
#           _count = next(self._counter)
            self._camera.annotate_text = Video.get_annotation()
#           if ( _count % 5 ) == 0: # every five seconds
            self.set_night_mode(camera, self.is_night_mode())
            time.sleep(1.0)

    # ..........................................................................
    def set_night_mode(self, camera, enabled):
        # NOTE: setting 'iso' overrides exposure mode
        _compass_calibrated = True if self._compass and self._compass.is_calibrated() else False
        if enabled:
            self._log.debug('night mode.')
#           camera.exposure_mode = 'nightpreview'
            '''
                off
                auto: use automatic exposure mode
                night: select setting for night shooting
                nightpreview:
                backlight: select setting for backlit subject
                spotlight:
                sports: select setting for sports (fast shutter etc.)
                snow: select setting optimised for snowy scenery
                beach: select setting optimised for beach
                verylong: select setting for long exposures
                fixedfps: constrain fps to a fixed value
                antishake: antishake mode
                fireworks: select setting optimised for fireworks

                source: https://www.raspberrypi.org/documentation/raspbian/applications/camera.md
            '''
            camera.iso = 800
            camera.led = False
            camera.annotate_foreground = Color.from_string('#ffdada')
            if _compass_calibrated:
                camera.annotate_background = Color.from_string('#440000')
            else:
                camera.annotate_background = Color.from_string('#440088')
            if self._ctrl_lights:
                self.set_lights(True)
        else:
            self._log.debug('day mode.')
            camera.iso = 100
#           camera.exposure_mode = 'off'
            camera.led = True
            camera.annotate_foreground = Color.from_string('#111111')
            if _compass_calibrated:
                camera.annotate_background = Color.from_string('#ffffff')
            else:
                camera.annotate_background = Color.from_string('#ffff00')
            if self._ctrl_lights:
                self.set_lights(False)

    # ..........................................................................
    def set_lights(self, on):
        if self._port_light and self._stbd_light:
            if on:
                self._port_light.light()
                self._stbd_light.light()
            else:
                self._port_light.clear()
                self._stbd_light.clear()


    # ..........................................................................
    def is_enabled(self):
        return self._enabled

    # ..........................................................................
    def start(self):
        if self._thread is not None:
            self._log.info('video already started.')
            return
        self._log.info('start.')
        self._enabled = True
        if not os.path.isdir(self._dirname):
            os.makedirs(self._dirname)
        self._filename = os.path.join(self._dirname, self._basename + '_' + self._get_timestamp() + '.h264')
        _output = OutputSplitter(self._filename)
        self._thread = threading.Thread(target=Video._start, args=[self, _output, lambda: self.is_enabled(), ])
        self._thread.setDaemon(True)
        self._thread.start()
        self._log.info(Fore.MAGENTA + Style.BRIGHT + 'video started. (flag: {})'.format(self._enabled))
#       self._log.info('started.')

    # ..........................................................................
    def stop(self):
        if self._thread is None:
            self._log.info('video already stopped.')
            return
        self._log.info('stopping video capture on file: {}'.format(self._filename))
        print(Fore.GREEN + 'setting enabled flag to False.' + Style.RESET_ALL)
        self._enabled = False

        if self._killer is not None:
            print(Fore.GREEN + 'KILLING...' + Style.RESET_ALL)
            self._killer()
        else:
            print(Fore.GREEN + 'NO KILLER.' + Style.RESET_ALL)

        if self._output is not None:
            print(Fore.GREEN + 'flushing and closing...' + Style.RESET_ALL)
            self._output.flush()
            self._output.close()
            self._output = None
            print(Fore.GREEN + 'closed.' + Style.RESET_ALL)
        self._log.info('joining thread...')
        self._thread.join(timeout=1.0)
        self._thread = None
        if self._convert_mp4:
            self._convert_to_mp4()
        self._log.info('stopped.')

    # ..........................................................................
    def _convert_to_mp4(self):
        if os.path.exists(self._filename):
            self._log.info('converting file {} to mp4...'.format(self._filename))
            _mp4_filename = Path(self._filename).stem + ".mp4"
            os.system('ffmpeg -loglevel panic -hide_banner -r {:d} -i {:s} -vcodec copy {:s}'.format(\
                    self._framerate, self._filename, _mp4_filename))
            self._log.info('mp4 conversion complete.')
            if self._remove_h264:
                os.remove(self._filename)
                self._log.info('removed h264 video source.')
        else:
            self._log.warning('could not convert to mp4: file {} did not exist.'.format(self._filename))

    # ..........................................................................
    def close(self, camera, output):
        self._log.info('closing video...')
        if self._ctrl_lights:
            self.set_lights(False)
        if camera:
            if camera.recording:
                camera.stop_recording()
                self._log.debug('camera stopped recording.')
            if not camera.closed:
                camera.close()
                self._log.debug('camera closed.')
        if output:
            output.flush()
            self._log.debug('output flushed.')
            output.close()
            self._log.debug('output closed.')
        self._log.info(Fore.MAGENTA + Style.BRIGHT + 'video closed.')


#EOF
