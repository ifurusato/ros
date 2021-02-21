#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# Copyright 2020 by Murray Altheim. All rights reserved. This file is part
# of the pimaster2ardslave project and is released under the MIT Licence;
# please see the LICENSE file included as part of this package.
#
# author:   Murray Altheim
# created:  2020-09-19
# modified: 2020-09-19
#

try:
    import ioexpander as io
except ImportError:
    exit("This script requires the ioexpander module\nInstall with: pip3 install --user pimoroni-ioexpander")

from lib.config_loader import ConfigLoader
from lib.logger import Level, Logger
#from lib.rate import Rate

# ..............................................................................
class Potentiometer(object):
    '''
       Configures a potentiometer (wired from Vcc to Gnd) connected to a single 
       pin on a Pimoroni IO Expander Breakout Garden board, returning an analog
       value scaled to a specified range. For a center-zero pot simply specify
       the minimum value as (-1.0 * out_max).
    '''
    def __init__(self, config, level):
        super().__init__()
        self._log = Logger('ioe', level)
        if config is None:
            raise ValueError('no configuration provided.')
        _config = config['ros'].get('potentiometer')
        self._pin         = _config.get('pin')
        self._log.info('pin assignment: {:d};'.format(self._pin))
        self._in_min      = _config.get('in_min')  # minimum analog value from IO Expander 
        self._in_max      = _config.get('in_max')  # maximum analog value from IO Expander 
        self._log.info('in range: {:d}-{:d}'.format(self._in_min, self._in_max))
        self._out_min     = _config.get('out_min') # minimum scaled output value
        self._out_max     = _config.get('out_max') # maximum scaled output value
        self._log.info('out range: {:>7.4f}-{:>7.4f}'.format(self._out_min, self._out_max))
        # configure board
        self._ioe = io.IOE(i2c_addr=0x18)
        self._ioe.set_adc_vref(3.3)  # input voltage of IO Expander, this is 3.3 on Breakout Garden
        # configure pin
        self._ioe.set_mode(self._pin, io.ADC)
        self._log.info('ready.')

    # ..........................................................................
    def set_out_max(self, out_max):
        self._out_max = out_max

    # ..........................................................................
    def get_value(self):
        '''
            Return the analog value as returned from the IO Expander board.
            This has been observed to be integers ranging from 0 to 330.
        '''
        return int(round(self._ioe.input(self._pin) * 100.0))

    # ..........................................................................
    def get_scaled_value(self):
        '''
                   (b-a)(x - min)
            f(x) = --------------  + a
                      max - min

            where: a = 0.0, b = 1.0, min = 0, max = 330.
        '''
        return (( self._out_max - self._out_min ) * ( self.get_value() - self._in_min ) / ( self._in_max - self._in_min )) + self._out_min

#EOF
