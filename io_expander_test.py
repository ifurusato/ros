#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# Copyright 2020 by Murray Altheim. All rights reserved. This file is part
# of the pimaster2ardslave project and is released under the MIT Licence;
# please see the LICENSE file included as part of this package.
#
# author:   Murray Altheim
# created:  2020-04-30
# modified: 2020-05-04
#
#  Tests the Pimoroni IO Expander Breakout Garden board, hardwired for five
#  Sharp analog infrared sensors and three bumper switches, with the specific
#  pin configuration coming from the YAML configuration file.
#
#  This writes directly to sysout using colorama for colored output.
#

import sys, time, traceback
import datetime as dt
import ioexpander as io
from colorama import init, Fore, Style
init()

from lib.config_loader import ConfigLoader
from lib.logger import Level, Logger
from lib.indicator import Indicator

# ..............................................................................
class IoExpander():
    def __init__(self, config, level):
        super().__init__()
        if config is None:
            raise ValueError('no configuration provided.')
        _config = config['ros'].get('io_expander')
        self._log = Logger('ioe', level)
        # infrared
        self._port_side_ir_pin = _config.get('port_side_ir_pin') # pin connected to port side infrared
        self._port_ir_pin      = _config.get('port_ir_pin')      # pin connected to port infrared
        self._center_ir_pin    = _config.get('center_ir_pin')    # pin connected to center infrared
        self._stbd_ir_pin      = _config.get('stbd_ir_pin')      # pin connected to starboard infrared
        self._stbd_side_ir_pin = _config.get('stbd_side_ir_pin') # pin connected to starboard side infrared
        self._log.info('IR pin assignments: port side: {:d}; port: {:d}; center: {:d}; stbd: {:d}; stbd side: {:d}.'.format(\
                self._port_side_ir_pin, self._port_ir_pin, self._center_ir_pin, self._stbd_ir_pin, self._stbd_side_ir_pin))
        # bumpers
        self._port_bmp_pin     = _config.get('port_bmp_pin')     # pin connected to port bumper
        self._center_bmp_pin   = _config.get('center_bmp_pin')   # pin connected to center bumper
        self._stbd_bmp_pin     = _config.get('stbd_bmp_pin')     # pin connected to starboard bumper
        self._log.info('BMP pin assignments: port: {:d}; center: {:d}; stbd: {:d}.'.format(\
                self._port_ir_pin, self._center_ir_pin, self._stbd_ir_pin ))

        # configure board
        self._ioe = io.IOE(i2c_addr=0x18)
        self.board = self._ioe # TEMP
        self._ioe.set_adc_vref(3.3)  # input voltage of IO Expander, this is 3.3 on Breakout Garden
        # analog infrared sensors
        self._ioe.set_mode(self._port_side_ir_pin, io.ADC)
        self._ioe.set_mode(self._port_ir_pin, io.ADC)
        self._ioe.set_mode(self._center_ir_pin, io.ADC)
        self._ioe.set_mode(self._stbd_ir_pin, io.ADC)
        self._ioe.set_mode(self._stbd_side_ir_pin, io.ADC)
        # digital bumpers
        self._ioe.set_mode(self._port_bmp_pin, io.PIN_MODE_PU)
        self._ioe.set_mode(self._center_bmp_pin, io.PIN_MODE_PU)
        self._ioe.set_mode(self._stbd_bmp_pin, io.PIN_MODE_PU)
        self._log.info('ready.')

    def get_port_side_ir_value(self):
        return int(round(self._ioe.input(self._port_side_ir_pin ) * 100.0))

    def get_port_ir_value(self):
        return int(round(self._ioe.input(self._port_ir_pin) * 100.0))

    def get_center_ir_value(self):
        return int(round(self._ioe.input(self._center_ir_pin) * 100.0))

    def get_stbd_ir_value(self):
        return int(round(self._ioe.input(self._stbd_ir_pin) * 100.0))

    def get_stbd_side_ir_value(self):
        return int(round(self._ioe.input(self._stbd_side_ir_pin) * 100.0))

    def get_port_bmp_value(self):
        return self._ioe.input(self._port_bmp_pin) == 0

    def get_center_bmp_value(self):
        return self._ioe.input(self._center_bmp_pin) == 0

    def get_stbd_bmp_value(self):
        return self._ioe.input(self._stbd_bmp_pin) == 0


# main .........................................................................
def main(argv):

    try:

        # read YAML configuration
        _loader = ConfigLoader(Level.INFO)
        filename = 'config.yaml'
        _config = _loader.configure(filename)

        _ioe = IoExpander(_config, Level.INFO)
        _board = _ioe.board
#       sys.exit(0)

#       _indicator = Indicator(Level.INFO)
        # add indicator as message consumer
#       _queue.add_consumer(_indicator)

        _max_value = 0

        # start...
        while True:

            _start_time = dt.datetime.now()

            _port_side_ir_value = _ioe.get_port_side_ir_value()
            _port_ir_value      = _ioe.get_port_ir_value()
            _center_ir_value    = _ioe.get_center_ir_value()
            _stbd_ir_value      = _ioe.get_stbd_ir_value()
            _stbd_side_ir_value = _ioe.get_stbd_side_ir_value()
            _port_bmp_value     = _ioe.get_port_bmp_value()
            _center_bmp_value   = _ioe.get_center_bmp_value()
            _stbd_bmp_value     = _ioe.get_stbd_bmp_value()

#           _port_side_ir_value = _board.input(_ioe._port_side_ir_pin )
#           _max_value = max(_max_value, _port_side_ir_value)
#           _port_ir_value      = _board.input(_ioe._port_ir_pin)
#           _max_value = max(_max_value, _port_ir_value)
#           _center_ir_value    = _board.input(_ioe._center_ir_pin)
#           _max_value = max(_max_value, _center_ir_value)
#           _stbd_ir_value      = _board.input(_ioe._stbd_ir_pin)
#           _max_value = max(_max_value, _stbd_ir_value)
#           _stbd_side_ir_value = _board.input(_ioe._stbd_side_ir_pin)
#           _max_value = max(_max_value, _stbd_side_ir_value)
#           _port_bmp_value     = _board.input(_ioe._port_bmp_pin) == 0
#           _max_value = max(_max_value, _port_bmp_value)
#           _center_bmp_value   = _board.input(_ioe._center_bmp_pin) == 0
#           _max_value = max(_max_value, _center_bmp_value)
#           _stbd_bmp_value     = _board.input(_ioe._stbd_bmp_pin) == 0
#           _max_value = max(_max_value, _stbd_bmp_value)

            _delta = dt.datetime.now() - _start_time
            _elapsed_ms = int(_delta.total_seconds() * 1000)

            print(Fore.RED       + 'PSIR: {:d} '.format(_port_side_ir_value) \
                  + Fore.MAGENTA + '\tPIR: {:d} '.format(_port_ir_value) \
                  + Fore.BLUE    + '\tCIR: {:d} '.format(_center_ir_value) \
                  + Fore.CYAN    + '\tSIR: {:d} '.format(_stbd_ir_value) \
                  + Fore.GREEN   + '\tSSIR: {:d} '.format(_stbd_side_ir_value) \
                  + Fore.MAGENTA + '\tPB: {} '.format(_port_bmp_value) \
                  + Fore.BLUE    + '\tCB: {} '.format(_center_bmp_value) \
                  + Fore.CYAN    + '\tSB: {} '.format(_stbd_bmp_value) \
                  + Fore.BLACK   + '\tmax: {:>5.2f} '.format(_max_value) \
                  + Fore.WHITE   + '\t{:>5.2f}ms elapsed.'.format(_elapsed_ms) + Style.RESET_ALL)

#           time.sleep(1.0 / 30)


    except KeyboardInterrupt:
        print(Fore.CYAN + Style.BRIGHT + 'caught Ctrl-C; exiting...')
        
    except Exception:
        print(Fore.RED + Style.BRIGHT + 'error starting IoExpander: {}'.format(traceback.format_exc()) + Style.RESET_ALL)

# call main ....................................................................
if __name__== "__main__":
    main(sys.argv[1:])

#EOF
