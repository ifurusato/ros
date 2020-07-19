#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# Copyright 2020 by Murray Altheim. All rights reserved. This file is part
# of the pimain2ardsubordinate project and is released under the MIT Licence;
# please see the LICENSE file included as part of this package.
#
# author:   Murray Altheim
# created:  2020-04-30
# modified: 2020-05-04
#
# This version uses smbus2 instead of pigpio.
#
#   % sudo pip3 install smbus2
#
# smbus2 notes from pololu: https://www.pololu.com/docs/0J73/15.9
#

import sys, time, traceback, itertools
from smbus2 import SMBus
#from smbus2 import SMBusWrapper
from colorama import init, Fore, Style
init()

from lib.pintype import PinType
from lib.logger import Logger, Level

#CLEAR_SCREEN = '\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n' # on MacOSX screen
CLEAR_SCREEN = '\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n'          # on Ubuntu screen
#CLEAR_SCREEN = '\n'  # no clear screen

# ..............................................................................
class I2cMain():
    '''
        A Raspberry Pi Main for a corresponding Arduino Subordinate.

        Parameters:
          device_id:  the I²C address over which the main and subordinate communicate
          level:      the log level, e.g., Level.INFO
    '''

    def __init__(self, config, level):
        super().__init__()
        if config is None:
            raise ValueError('no configuration provided.')
        self._config = config['ros'].get('i2c_main')
        self._device_id  = self._config.get('device_id') # i2c hex address of subordinate device, must match Arduino's SLAVE_I2C_ADDRESS
        self._channel = self._config.get('channel')

        self._log = Logger('i²cmain-0x{:02x}'.format(self._device_id), level)
        self._log.info('initialising...')
        self._counter = itertools.count()
        self._loop_count = 0  # currently only used in testing
        self._closed = False
        self._i2c = SMBus(self._channel)
        self._log.info('ready: imported smbus2 and obtained I²C bus at address 0x{:02X}...'.format(self._device_id))


    # ..............................................................................
    def read_i2c_data(self):
        '''
            Read two bytes (LSB, MSB) from the I²C device at the specified handle, returning the value as an int.
        '''
        with SMBus(self._channel) as bus:
            _low_byte  = bus.read_byte_data(self._device_id, 0)
            _high_byte = bus.read_byte_data(self._device_id, 1)
#           _high_byte = bus.read_byte(self._device_id)
#           _low_byte  = bus.read_byte(self._device_id)
        _data      = _low_byte
        _data     += ( _high_byte << 8 )
        self._log.debug('read 2 bytes:  hi: {:08b} lo: {:08b} as data: {}'.format(_high_byte, _low_byte, _data))
        return _data


    # ..........................................................................
    def write_i2c_data(self, data):
        '''
            Write an int as two bytes (LSB, MSB) to the I²C device at the specified handle.
        '''
        byteArray = [ data, ( data >> 8 ) ]
        with SMBus(self._channel) as bus:
            bus.write_byte(self._device_id, byteArray[0])
            bus.write_byte(self._device_id, byteArray[1])
        self._log.debug('wrote 2 bytes: hi: {:08b};\t lo: {:08b};\t sent data: {}'.format(byteArray[1], byteArray[0], data))


    # ..........................................................................
    def get_input_from_pin(self, pinPlusOffset):
        '''
            Sends a message to the pin (which should already include an offset if
            this is intended to return a non-pin value), returning the result.
        '''
        self.write_i2c_data(pinPlusOffset)
        _received_data  = self.read_i2c_data()
        self._log.debug('received response from pin {:d} of {:>5.2f}.'.format(pinPlusOffset, _received_data))
        return _received_data


    # ..........................................................................
    def set_output_on_pin(self, pin, value):
        '''
            Set the output on the pin as true (HIGH) or false (LOW). The
            corresponding pin must have already been configured as OUTPUT.
            This returns the response from the Arduino.
        '''
        if value is True:
            self.write_i2c_data(pin + 192)
            self._log.debug('set pin {:d} as HIGH.'.format(pin))
        else:
            self.write_i2c_data(pin + 160)
            self._log.debug('set pin {:d} as LOW.'.format(pin))
        _received_data  = self.read_i2c_data()
        self._log.debug('received response on pin {:d} of {:>5.2f}.'.format(pin, _received_data))
        return _received_data


    # ..........................................................................
    def configure_pin_as_digital_input(self, pin):
        '''
            Equivalent to calling pinMode(pin, INPUT), which sets the pin as a digital input pin.

            This configuration treats the output as a digital value, returning a 0 (inactive) or 1 (active).

            32-63:      set the pin (n-32) as an INPUT pin, return pin number
        '''
        self._log.debug('configuring pin {:d} for DIGITAL_INPUT...'.format(pin))
        self.write_i2c_data(pin + 32)
        _received_data  = self.read_i2c_data()
        if pin == _received_data:
            self._log.info('configured pin {:d} for DIGITAL_INPUT'.format(pin))
        else:
            _err_msg = self.get_error_message(_received_data)
            self._log.error('failed to configure pin {:d} for DIGITAL_INPUT; response: {}'.format(pin, _err_msg))


    # ..........................................................................
    def configure_pin_as_digital_input_pullup(self, pin):
        '''
            Equivalent to calling pinMode(pin, INPUT_PULLUP), which sets the pin as a
            digital input pin with an internal pullup resister.

            This configuration treats the output as a digital value, returning a 0 (active) or 1 (inactive).

            64-95:      set the pin (n-64) as an INPUT_PULLUP pin, return pin number
        '''
        self._log.debug('configuring pin {:d} for DIGITAL_INPUT_PULLUP'.format(pin))
        self.write_i2c_data(pin + 64)
        _received_data  = self.read_i2c_data()
        if pin == _received_data:
            self._log.info('configured pin {:d} for DIGITAL_INPUT_PULLUP'.format(pin))
        else:
            _err_msg = self.get_error_message(_received_data)
            self._log.error('failed to configure pin {:d} for DIGITAL_INPUT_PULLUP; response: {}'.format(pin, _err_msg))


    # ..........................................................................
    def configure_pin_as_analog_input(self, pin):
        '''
            Equivalent to calling pinMode(pin, INPUT);
            which sets the pin as an input pin.

            This configuration treats the output as an analog value, returning a value from 0 - 255.

            96-127:     set the pin (n-96) as an INPUT_ANALOG pin, return pin number
        '''
        self._log.debug('configuring pin {:d} for ANALOG_INPUT...'.format(pin))
        self.write_i2c_data(pin + 96)
        _received_data = self.read_i2c_data()
        if pin == _received_data:
            self._log.info('configured pin {:d} for ANALOG_INPUT'.format(pin))
        else:
            _err_msg = self.get_error_message(_received_data)
            self._log.error('failed to configure pin {:d} for ANALOG_INPUT; response: {}'.format(pin, _err_msg))


    # ..........................................................................
    def configure_pin_as_output(self, pin):
        '''
            Equivalent to calling pinMode(pin, OUTPUT), which sets the pin as an output pin.

            The output from calling this pin returns the current output setting. To set the
            value to 0 or 1 call setOutputForPin().

            128-159:    set the pin (n-128) as an OUTPUT pin, return pin number
        '''
        self._log.debug('configuring pin {:d} for OUTPUT...'.format(pin))
        self.write_i2c_data(pin + 128)
        _received_data = self.read_i2c_data()
        if pin == _received_data:
            self._log.info('configured pin {:d} for OUTPUT'.format(pin))
        else:
            _err_msg = self.get_error_message(_received_data)
            self._log.error('failed to configure pin {:d} for OUTPUT; response: {}'.format(pin, _err_msg))


    # ..........................................................................
    def get_error_message(self, n):
        '''
            These match the error numbers in the Arduino sketch.
        '''
        switcher = {
            249: "249: EMPTY_QUEUE",            # returned on error
            250: "250: PIN_UNASSIGNED",         # configuration error
            251: "251: PIN_ASSIGNED_AS_OUTPUT", # configuration error
            252: "252: PIN_ASSIGNED_AS_INPUT",  # configuration error
            253: "253: TOO_MUCH_DATA",          # returned on communications error
            254: "254: UNRECOGNISED_COMMAND",   # returned on communications error
            255: "255: UNDEFINED_ERROR"         # returned on any other error
        }
        return switcher.get(n, "{}: UNRECOGNISED_ERROR".format(n))


    # ..........................................................................
    def close(self):
        '''
            Close the instance.
        '''
        self._log.debug('closing I²C main.')
        if not self._closed:
            try:
                self._closed = True
#               self._pi.i2c_close(self._handle) # close device
                self._log.debug('I²C main closed.')
            except Exception as e:
                self._log.error('error closing main: {}'.format(e))
        else:
            self._log.debug('I²C main already closed.')


    # ..........................................................................
    def front_sensor_loop(self, queue, enabled, loop_delay_sec, callback):
        '''
            Configures each of the pin types based on the application-level YAML 
            configuration file, then starts a loop that continues while enabled.
            This passes incoming events from the Arduino to the message queue.

            The prototype (KR01) configuration includes:

              *  0:  starboard side analog infrared sensor.
              *  1:  starboard analog infrared sensor.
              *  2:  center analog infrared sensor.
              *  3:  port analog infrared sensor.
              *  4:  port side analog infrared sensor.
              *  9:  starboard bumper (digital).
              *  10: center bumper (digital).
              *  11: port bumper (digital).

             Analog sensors return a value from 0-255, digital 0 or 1.
        '''
        try:

            self._log.info('front_sensor_loop: configuring the arduino and then reading the results...')

            _assignment_config = self._config.get('assignments')
            _assignments = {}
            # configure pins...
            for pin, pin_type_param in _assignment_config.items():
                pin_type = PinType.from_str(pin_type_param)
                self._log.debug('configuring pin {}:\ttype: {}.'.format( pin, pin_type.description))
                _assignments.update({ pin : pin_type })
                if pin_type is PinType.DIGITAL_INPUT: # configure pin as DIGITAL_INPUT
                    self.configure_pin_as_digital_input(pin)
                elif pin_type is PinType.DIGITAL_INPUT_PULLUP: # configure pin as DIGITAL_INPUT_PULLUP
                    self.configure_pin_as_digital_input_pullup(pin)
                elif pin_type is PinType.ANALOG_INPUT: # configure pin as ANALOG_INPUT
                    self.configure_pin_as_analog_input(pin)
#               elif pin_type is PinType.OUTPUT: # configure pin as OUTPUT
#                   self.configure_pin_as_output(pin)

            self._log.info('configured. starting event loop...\n')
            while enabled:
                _count = next(self._counter)
                print(CLEAR_SCREEN)
                for pin in _assignments:
                    pin_type = _assignments[pin]
                    self._log.debug('reading from pin {}:\ttype: {}.'.format( pin, pin_type.description))
                    # write and then read response to/from Arduino...
                    _data_to_send = pin
                    self.write_i2c_data(_data_to_send)
                    _received_data = self.read_i2c_data()
                    callback(pin, pin_type, _received_data)
                time.sleep(loop_delay_sec)

            # we never get here if using 'while True:'
            self._log.info('exited event loop.')

        except KeyboardInterrupt:
            self._log.warning('Ctrl-C caught; exiting...')
        except Exception as e:
            self._log.error('error in main: {}'.format(e))
            traceback.print_exc(file=sys.stdout)
#       finally:
#           self.close()
#           self._log.info('complete.')



    # tests ====================================================================

    # ..........................................................................
    def test_echo(self):
        '''
            Performs a simple test, sending a series of bytes to the subordinate, then
            reading the return values. The Arduino subordinate's 'isEchoTest' boolean
            must be set to true. This does not require any hardware configuration
            save that the Raspberry Pi must be connected to the Arduino via I²C
            and that there is no contention on address 0x08.
        '''
        try:
            self._log.info('starting echo test...')
            _data = [ 0, 1, 2, 4, 32, 63, 64, 127, 128, 228, 254, 255 ]
            for i in range(0,len(_data)):
                _data_to_send = _data[i]
                self.write_i2c_data(_data_to_send)
                _received_data = self.read_i2c_data()
                if _data_to_send != _received_data:
                    self._log.error('echo failed:   {} != {}'.format(_data_to_send, _received_data))
                else:
                    self._log.info('echo succeeded: {} == {}'.format(_data_to_send, _received_data))

#           self._pi.i2c_close()
            self._log.info('echo test complete.')
        except Exception as e:
            self._log.error('error in echo test: {}'.format(e))
            traceback.print_exc(file=sys.stdout)


    # ..........................................................................
    def test_blink_led(self, pin, blink_count):
        '''
            Blinks an LED connected to the specified pin of the Arduino. If you're
            using a 5V Arduino a 330 ohm resistor should be connected in series
            with the LED, as LEDs cannot directly handle a 5v source.
        '''
        try:

            self._log.info(Fore.CYAN + Style.BRIGHT + 'blink the LED {:d} times...'.format(blink_count))
            self._log.info(Fore.YELLOW + Style.BRIGHT + 'type Ctrl-C to cancel the test.')

            # configure an LED as OUTPUT on specified pin
            self.configure_pin_as_output(pin)

            # 225: set request count to zero
            request_count = self.get_input_from_pin(225)
            self._log.info('set loop count to zero; response: {:>5.2f}'.format(request_count))

#           while True: # if you want to blink foreever
            for i in range(blink_count):
                _received_data = self.set_output_on_pin(pin, True)
                self._log.debug(Fore.YELLOW + 'blink ON  on pin {:d}; response: {:>5.2f}'.format(pin, _received_data))
                time.sleep(0.025)

                _received_data = self.set_output_on_pin(pin, False)
                self._log.debug(Fore.MAGENTA + 'blink OFF on pin {:d}; response: {:>5.2f}'.format(pin, _received_data))
                time.sleep(0.015)

            # 226: return request count (we expect 2x the blink count plus one for the request count itself
            _expected = 2 * ( blink_count * 2 + 1 )
            request_count = self.get_input_from_pin(226)
            if _expected == request_count:
                self._log.info(Style.BRIGHT + 'request count: ' + Fore.CYAN + Style.NORMAL + 'expected: {:d}; actual: {:d}'.format(_expected, request_count))
            else:
                self._log.warning('request count: ' + Fore.CYAN + Style.NORMAL + 'expected: {:d}; actual: {:d}'.format(_expected, request_count))

        except KeyboardInterrupt:
            self._log.warning('Ctrl-C caught; exiting...')
        except Exception as e:
            self._log.error('error in main: {}'.format(e))
            traceback.print_exc(file=sys.stdout)


    # ..........................................................................
    def test_configuration(self, loop_count):
        '''
            Configures each of the pin types based on the application-level YAML 
            configuration. You can see the result of the configuration on the 
            Arduino IDE's Serial Monitor (even without any associated hardware). 
            If you set up the hardware to match this configuration you can also 
            see the input and output results on the Serial Monitor.

            The prototype hardware configuration is as follows:

              *  An LED (and a 330 ohm resistor) connected between pin 7 and ground, configured as OUTPUT.
              *  A pushbutton connected between pin 9 and ground, configured as INPUT_PULLUP.
              *  A digital infrared sensor connected to pin 10, configured as INPUT.
              *  A digital infrared sensor connected to pin 11, configured as INPUT_PULLUP.
              *  An analog infrared sensor connected to pin A1, configured as INPUT.
        '''
        try:

            self._log.info(Fore.CYAN + Style.BRIGHT + 'test configuring the arduino and then reading the results...')
            self._log.info(Fore.YELLOW + Style.BRIGHT + 'type Ctrl-C to cancel the test.')

            LOOP_DELAY_SEC = 1

            _assignment_config = self._config.get('assignments')
            _assignments = {}
            for pin, pin_type_param in _assignment_config.items():
                pin_type = PinType.from_str(pin_type_param)
                self._log.debug('configuring pin {}:\ttype: {}.'.format( pin, pin_type.description))
                _assignments.update({ pin : pin_type })
                if pin_type is PinType.DIGITAL_INPUT: # configure pin as DIGITAL_INPUT
                    self.configure_pin_as_digital_input(pin)
                elif pin_type is PinType.DIGITAL_INPUT_PULLUP: # configure pin as DIGITAL_INPUT_PULLUP
                    self.configure_pin_as_digital_input_pullup(pin)
                elif pin_type is PinType.ANALOG_INPUT: # configure pin as ANALOG_INPUT
                    self.configure_pin_as_analog_input(pin)
                elif pin_type is PinType.OUTPUT: # configure pin as OUTPUT
                    self.configure_pin_as_output(pin)

            self._log.info('configured. starting loop to repeat {:d} times...\n'.format(loop_count))
            for x in range(loop_count):
                _count = next(self._counter)
                print(CLEAR_SCREEN)
                for pin in _assignments:
                    pin_type = _assignments[pin]
                    self._log.debug('reading from pin {}:\ttype: {}.'.format( pin, pin_type.description))
                    _data_to_send = pin
                    # write and then read response to/from Arduino...
                    self.write_i2c_data(_data_to_send)
                    _received_data = self.read_i2c_data()
                    _is_close = _received_data > 100.0
                    if pin_type is PinType.DIGITAL_INPUT: # configure pin as DIGITAL_INPUT
                        self._log.info('[{:04d}] DIGITAL IR ({:d}):      \t'.format(_count, pin) + Fore.CYAN + Style.BRIGHT  + '{:d}'.format(_received_data) + Style.DIM + '\t(displays digital value 0|1)')
                    elif pin_type is PinType.DIGITAL_INPUT_PULLUP: # configure pin as DIGITAL_INPUT_PULLUP
                        self._log.info('[{:04d}] DIGITAL IR ({:d}):      \t'.format(_count, pin) + Fore.GREEN + Style.BRIGHT  + '{:d}'.format(_received_data) + Style.DIM + '\t(displays digital pup value 0|1)')
                    elif pin_type is PinType.ANALOG_INPUT: # configure pin as ANALOG_INPUT
                        _close_color = Fore.RED if _is_close else Fore.YELLOW
                        self._log.info('[{:04d}] ANALOG IR ({:d}):       \t'.format(_count, pin) + _close_color + Style.BRIGHT + '{:d}'.format(_received_data) + Style.DIM + '\t(analog value 0-255)')
                    elif pin_type is PinType.OUTPUT: # configure pin as OUTPUT
                        self._log.info('[{:04d}] LED ({:d}):             \t'.format(_count, pin) + Fore.MAGENTA + Style.BRIGHT + '{:d}'.format(_received_data) + Style.DIM + '\t(expected 251/PIN_ASSIGNED_AS_OUTPUT)')

                print('')
                time.sleep(LOOP_DELAY_SEC)

            # we never get here if using 'while True:'
            self._log.info('test complete.')

        except KeyboardInterrupt:
            self._log.warning('Ctrl-C caught; exiting...')
        except Exception as e:
            self._log.error('error in main: {}'.format(e))
            traceback.print_exc(file=sys.stdout)
#       finally:
#           self.close()
#           self._log.info('complete.')


#EOF
