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
#  This version uses smbus2 instead of pigpio.
#
#   % sudo pip3 install smbus2
#
#  smbus2 notes from pololu: https://www.pololu.com/docs/0J73/15.9
#

import sys, time, traceback, itertools, threading
from colorama import init, Fore, Style
init()

try:
    from smbus2 import SMBus
except Exception:
    sys.exit("This script requires the smbus2 module.\nInstall with: sudo pip3 install smbus2")

from lib.pintype import PinType
from lib.logger import Logger, Level

#CLEAR_SCREEN = '\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n' # on MacOSX screen
#CLEAR_SCREEN = '\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n'          # on Ubuntu screen
CLEAR_SCREEN = '\n\n'  # no clear screen

# ..............................................................................
class I2cMaster():
    '''
        A Raspberry Pi Master for a corresponding Arduino Slave.

        Parameters:
          device_id:  the I²C address over which the master and slave communicate
          level:      the log level, e.g., Level.INFO
    '''

    def __init__(self, config, level):
        super().__init__()
        if config is None:
            raise ValueError('no configuration provided.')
        self._config = config['ros'].get('i2c_master')
        self._device_id = self._config.get('device_id') # i2c hex address of slave device, must match Arduino's SLAVE_I2C_ADDRESS
        self._channel = self._config.get('channel')

        self._log = Logger('i²cmaster-0x{:02x}'.format(self._device_id), level)
        self._log.info('initialising...')
        self._counter = itertools.count()
        self._loop_count = 0  # currently only used in testing
        self._thread = None
        self._enabled = False
        self._closed = False
        self._i2c = SMBus(self._channel)
        self._log.info('ready: imported smbus2 and obtained I²C bus at address 0x{:02X}...'.format(self._device_id))


    # ..........................................................................
    def enable(self):
        self._enabled = True
        self._log.info('enabled.')


    # ..........................................................................
    def disable(self):
        self._enabled = False
        self._log.info('disabled.')


    # ..............................................................................
    def read_i2c_data(self):
        '''
            Read a byte from the I²C device at the specified handle, returning the value.

            ## Examples:
            int.from_bytes(b'\x00\x01', "big")        # 1
            int.from_bytes(b'\x00\x01', "little")     # 256
        '''
        with SMBus(self._channel) as bus:
            _byte = bus.read_byte_data(self._device_id, 0)
            time.sleep(0.01)
        return _byte


    # ..........................................................................
    def write_i2c_data(self, data):
        '''
            Write a byte to the I²C device at the specified handle.
        '''
        with SMBus(self._channel) as bus:
            bus.write_byte(self._device_id, data)
            time.sleep(0.01)


    # ..........................................................................
    def get_input_from_pin(self, pin):
        '''
            Sends a message to the pin, returning the result as a byte.
        '''
        self.write_i2c_data(pin)
#       time.sleep(0.2)
        _received_data  = self.read_i2c_data()
#       time.sleep(0.2)
        self._log.debug('received response from pin {:d} of {:08b}.'.format(pin, _received_data))
        return _received_data


    # ..........................................................................
    def in_loop(self):
        '''
            Returns true if the main loop is active (the thread is alive).
        '''
        return self._thread != None and self._thread.is_alive()


    # ..........................................................................
    def _front_sensor_loop(self, loop_delay_sec, callback):
        self._log.info('starting event loop...\n')
        while self._enabled:

            _count = next(self._counter)
            print(CLEAR_SCREEN)

            # pin 1: analog infrared sensor ................
            _received_data = self.get_input_from_pin(1)
#           self._log.info('[{:04d}] ANALOG IR ({:d}):       \t'.format(_count, 1) + ( Fore.RED if ( _received_data > 100.0 ) else Fore.YELLOW ) \
#                   + Style.BRIGHT + '{:d}'.format(_received_data) + Style.DIM + '\t(analog value 0-255)')
            callback(1, PinType.ANALOG_INPUT, _received_data)

            # pin 2: analog infrared sensor ................
            _received_data = self.get_input_from_pin(2)
#           self._log.info('[{:04d}] ANALOG IR ({:d}):       \t'.format(_count, 2) + ( Fore.RED if ( _received_data > 100.0 ) else Fore.YELLOW ) \
#                   + Style.BRIGHT + '{:d}'.format(_received_data) + Style.DIM + '\t(analog value 0-255)')
            callback(2, PinType.ANALOG_INPUT, _received_data)

            # pin 3: analog infrared sensor ................
            _received_data = self.get_input_from_pin(3)
#           self._log.info('[{:04d}] ANALOG IR ({:d}):       \t'.format(_count, 3) + ( Fore.RED if ( _received_data > 100.0 ) else Fore.YELLOW ) \
#                   + Style.BRIGHT + '{:d}'.format(_received_data) + Style.DIM + '\t(analog value 0-255)')
            callback(3, PinType.ANALOG_INPUT, _received_data)

            # pin 4: analog infrared sensor ................
            _received_data = self.get_input_from_pin(4)
#           self._log.info('[{:04d}] ANALOG IR ({:d}):       \t'.format(_count, 4) + ( Fore.RED if ( _received_data > 100.0 ) else Fore.YELLOW ) \
#                   + Style.BRIGHT + '{:d}'.format(_received_data) + Style.DIM + '\t(analog value 0-255)')
            callback(4, PinType.ANALOG_INPUT, _received_data)

            # pin 5: analog infrared sensor ................
            _received_data = self.get_input_from_pin(5)
#           self._log.info('[{:04d}] ANALOG IR ({:d}):       \t'.format(_count, 5) + ( Fore.RED if ( _received_data > 100.0 ) else Fore.YELLOW ) \
#                   + Style.BRIGHT + '{:d}'.format(_received_data) + Style.DIM + '\t(analog value 0-255)')
            callback(5, PinType.ANALOG_INPUT, _received_data)

            # pin 9: digital bumper sensor .................
            _received_data = self.get_input_from_pin(9)
#           self._log.info('[{:04d}] DIGITAL IR ({:d}):      \t'.format(_count, 9) + Fore.GREEN + Style.BRIGHT  + '{:d}'.format(_received_data) \
#                   + Style.DIM + '\t(displays digital pup value 0|1)')
            callback(9, PinType.DIGITAL_INPUT_PULLUP, _received_data)

            # pin 10: digital bumper sensor ................
            _received_data = self.get_input_from_pin(10)
#           self._log.info('[{:04d}] DIGITAL IR ({:d}):      \t'.format(_count, 10) + Fore.GREEN + Style.BRIGHT  + '{:d}'.format(_received_data) \
#                   + Style.DIM + '\t(displays digital pup value 0|1)')
            callback(10, PinType.DIGITAL_INPUT_PULLUP, _received_data)

            # pin 11: digital bumper sensor ................
            _received_data = self.get_input_from_pin(11)
#           self._log.info('[{:04d}] DIGITAL IR ({:d}):      \t'.format(_count, 11) + Fore.GREEN + Style.BRIGHT  + '{:d}'.format(_received_data) \
#                   + Style.DIM + '\t(displays digital pup value 0|1)')
            callback(11, PinType.DIGITAL_INPUT_PULLUP, _received_data)

            time.sleep(loop_delay_sec)

        # we never get here if using 'while True:'
        self._log.info('exited event loop.')


    # ..........................................................................
    def start_front_sensor_loop(self, loop_delay_sec, callback):
        '''
            This is the method to call to actually start the loop.
        '''
        if not self._enabled:
            raise Exception('attempt to start front sensor event loop while disabled.')
        elif not self._closed:
            if self._thread is None:
                enabled = True
                self._thread = threading.Thread(target=I2cMaster._front_sensor_loop, args=[self, loop_delay_sec, callback])
                self._thread.start()
                self._log.info('started.')
            else:
                self._log.warning('cannot enable: process already running.')
        else:
            self._log.warning('cannot enable: already closed.')


    # ..........................................................................
    def close(self):
        '''
            Close the instance.
        '''
        self._log.debug('closing I²C master.')
        if not self._closed:
            try:
                if self._thread != None:
                    self._thread.join(timeout=1.0)
                    self._log.debug('front sensor loop thread joined.')
                    self._thread = None
                self._closed = True
#               self._pi.i2c_close(self._handle) # close device
                self._log.debug('I²C master closed.')
            except Exception as e:
                self._log.error('error closing master: {}'.format(e))
        else:
            self._log.debug('I²C master already closed.')


#EOF
