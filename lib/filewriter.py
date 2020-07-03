#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# Copyright 2020 by Murray Altheim. All rights reserved. This file is part of
# the Robot Operating System project and is released under the "Apache Licence, 
# Version 2.0". Please see the LICENSE file included as part of this package.
#
# author:   Murray Altheim
# created:  2020-04-15

import os, time, threading, traceback
from string import Template
from datetime import datetime
from colorama import init, Fore, Style
init()

from lib.logger import Logger, Level

# ..............................................................................
class FileWriter():
    '''
        The FileWriter writes content to a file located in a directory (set
        in configuration) which will be created if it doesn't yet exist.

        It must be enabled in order to start its data write thread.

        It two options:

          * filename:  the optional filename of the output file. If unspecified,
                       the filename used will include a timestamp. 
          * level:     the Log level
    '''
    def __init__(self, config, filename, level):
        self._log = Logger("filewriter", level)
        self._enabled = False
        self._active = False
        self._thread = None
        # configuration ..............................................
        cfg = config['ros'].get('filewriter')
        _extension = cfg.get('extension')
        _directory_name = cfg.get('directory_name')
        _default_filename_prefix = cfg.get('default_filename_prefix')
        self._gnuplot_template_file = cfg.get('gnuplot_template_file')  # template for gnuplot settings
        self._gnuplot_output_file = cfg.get('gnuplot_output_file')      # output file for gnuplot settings
        if not os.path.exists(_directory_name):
            os.makedirs(_directory_name)
        if filename is not None:
            if filename.endswith(_extension):
                self._filename = _directory_name + '/' + filename
            else:
                self._filename = _directory_name + '/' + filename + _extension
        else:        
            # create os-friendly filename including current timestamp
            self._filename = _directory_name + '/' + _default_filename_prefix \
                    + datetime.utcfromtimestamp(datetime.utcnow().timestamp()).isoformat().replace(':','_').replace('-','_').replace('.','_') + _extension
        self._log.info('ready.')


    # ..........................................................................
    def get_filename(self):
        return self._filename


    # ..........................................................................
    def is_enabled(self):
        return self._enabled


    # ..........................................................................
    def enable(self, queue):
        '''
            Enables and starts the data collection thread using a 
            producer-consumer pattern. The passed parameters include the 
            deque that will be actively populated with data by the producer.
        '''
        if self._thread is None:
            self._enabled = True
            self._log.debug('starting file writer thread...')
            self._thread = threading.Thread(target=FileWriter._writer, args=[self, queue, lambda: self.is_enabled(), ])
            self._thread.start()
            self._log.debug('enabled.')
        else:
            self._log.warning('already enabled.')


    # ..........................................................................
    def disable(self):
        if self._enabled:
            self._enabled = False
            self._log.info('closing...')
            while self._active:
                self._log.warning('waiting for file writer to close...')
                time.sleep(0.5)
            self._log.info('joining file write thread...')
            self._thread.join()
            self._thread = None
            self._log.info('file write thread joined.')
            self._log.info('closed.')
        else:
            self._log.info('already closed.')
            

    # ..........................................................................
    def write_gnuplot_settings(self, data):
        '''
            Using the provided array of data, reads in the gnuplot template,
            substitutes the data arguments into the imported string, then 
            writes the output file as the gnuplot settings file.
        '''
        try:
            # read template for gnuplot settings
            _fin = open(self._gnuplot_template_file, "r")
            _string = _fin.read()
            _template = Template(_string)
            _elapsed = data[0]
            self._log.debug('ELAPSED={}'.format(_elapsed))
            _output = _template.substitute(ELAPSED_SEC=_elapsed)
            _fout = open(self._gnuplot_output_file, "w")
            _fout.write(_output)
            _fout.close()
            self._log.info('wrote gnuplot settings to file: {}'.format(self._gnuplot_output_file))
        except Exception as e:
            self._log.error('error writing gnuplot settings: {}'.format(traceback.format_exc()))


    # ..........................................................................
    def _writer(self, queue, f_is_enabled):
        self._log.info('writing to file: {}...'.format(self._filename))
        self._active = True
        fieldnames = ['time', 'value']
        try:
            _file = open(self._filename, mode='w')
            with _file as output_file:
                while f_is_enabled():
                    while len(queue) > 0:
                        _data = queue.pop()
                        _file.write(_data)
                        self._log.debug('wrote row {}'.format(_data))
                    time.sleep(0.01)
            self._log.info('exited file write loop.')
        finally:
            if _file:
                _file.close()
                self._log.info('file closed.')
            self._active = False
        self._log.info('file write thread complete.')


#EOF
