#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# Copyright 2020 by Murray Altheim. All rights reserved. This file is part of
# the Robot OS project and is released under the "Apache Licence, Version 2.0".
# Please see the LICENSE file included as part of this package.
#
# author:   altheim
# created:  2020-01-18
# modified: 2020-02-06
#
# Implements an Integrated Front Sensor using an IO Expander Breakout Garden
# board. This polls the values of the board's pins, which outputs 0-255 values
# for analog pins, and a 0 or 1 for digital pins.
#

import sys, time, traceback, threading, itertools
import datetime as dt
from colorama import init, Fore, Style
init()

import ioexpander as io

from lib.config_loader import ConfigLoader
from lib.pintype import PinType
from lib.logger import Logger, Level
from lib.event import Event
from lib.message import Message

from lib.indicator import Indicator

CLEAR_SCREEN = '\n'  # no clear screen

# ..............................................................................
class MockMessageQueue():
    '''
        This message queue waits for at least one infrared event of each type.
    '''
    def __init__(self, level):
        super().__init__()
        self._counter = itertools.count()
        self._log = Logger("mock queue", Level.INFO)
        self._log.info('ready.')

    # ......................................................
    def add(self, message):
        message.set_number(next(self._counter))
        self._log.info('added message #{}: priority {}: {}'.format(message.get_number(), message.get_priority(), message.get_description()))
        event = message.get_event()
        if event is Event.INFRARED_PORT_SIDE:
            self._log.info(Fore.RED + Style.BRIGHT + 'INFRARED_PORT_SIDE: {}'.format(event.description))
        elif event is Event.INFRARED_PORT:
            self._log.info(Fore.MAGENTA + Style.BRIGHT + 'INFRARED_PORT: {}'.format(event.description))
        elif event is Event.INFRARED_CNTR:
            self._log.info(Fore.BLUE + Style.BRIGHT + 'INFRARED_PORT: {}'.format(event.description))
        elif event is Event.INFRARED_STBD:
            self._log.info(Fore.CYAN + Style.BRIGHT + 'INFRARED_PORT: {}'.format(event.description))
        elif event is Event.INFRARED_STBD_SIDE:
            self._log.info(Fore.GREEN + Style.BRIGHT + 'INFRARED_PORT: {}'.format(event.description))
        elif event is Event.BUMPER_PORT:
            self._log.info(Fore.RED + Style.BRIGHT + 'BUMPER_PORT: {}'.format(event.description))
        elif event is Event.BUMPER_CNTR:
            self._log.info(Fore.BLUE + Style.BRIGHT + 'BUMPER_CNTR: {}'.format(event.description))
        elif event is Event.BUMPER_STBD:
            self._log.info(Fore.GREEN + Style.BRIGHT + 'BUMPER_STBD: {}'.format(event.description))
        else:
            self._log.info(Fore.BLACK + Style.BRIGHT + 'other event: {}'.format(event.description))

    # ......................................................
    def is_complete(self):
        return not self._events

    # ......................................................
    def _display_event_list(self):
        self._log.info('\n' + Fore.BLUE + Style.BRIGHT + '{} events remain in list:'.format(len(self._events)))
        for e in self._events:
            self._log.info(Fore.BLUE + Style.BRIGHT + '{}'.format(e.description))


# ..............................................................................
class IoExpander():
    '''
        Wraps an IO Expander board as input from an integrated front sensor
        array of infrareds and bumper switches.
    '''
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


# ..............................................................................
class IntegratedFrontSensor():
    '''
        IntegratedFrontSensor: communicates with the integrated front bumpers 
        and infrared sensors, receiving messages from the I²C Arduino slave,
        sending the messages with its events onto the message bus.
        
        Parameters:
    
           config: the YAML based application configuration
           queue:  the message queue receiving activation notifications
           level:  the logging Level
    
        Usage:
    
           _ifs = IntegratedFrontSensor(_config, _queue, Level.INFO)
           _ifs.enable()
    '''

    # ..........................................................................
    def __init__(self, config, queue, level):
        if config is None:
            raise ValueError('no configuration provided.')
        self._config = config['ros'].get('integrated_front_sensor')
        self._queue = queue
        self._log = Logger("ifs", level)
        self._device_id                  = self._config.get('device_id') # i2c hex address of slave device, must match Arduino's SLAVE_I2C_ADDRESS
        self._channel                    = self._config.get('channel')
        self._ignore_duplicates = False # TODO set from config
        # hardware pin assignments
        self._port_side_ir_pin           = self._config.get('port_side_ir_pin')
        self._port_ir_pin                = self._config.get('port_ir_pin')
        self._center_ir_pin              = self._config.get('center_ir_pin')
        self._stbd_ir_pin                = self._config.get('stbd_ir_pin')
        self._stbd_side_ir_pin           = self._config.get('stbd_side_ir_pin')
        self._port_bmp_pin               = self._config.get('port_bmp_pin')
        self._center_bmp_pin             = self._config.get('center_bmp_pin')
        self._stbd_bmp_pin               = self._config.get('stbd_bmp_pin')
        # short distance:
        self._port_side_trigger_distance = self._config.get('port_side_trigger_distance')
        self._port_trigger_distance      = self._config.get('port_trigger_distance')
        self._center_trigger_distance    = self._config.get('center_trigger_distance')
        self._stbd_trigger_distance      = self._config.get('stbd_trigger_distance')
        self._stbd_side_trigger_distance = self._config.get('stbd_side_trigger_distance')
        self._log.info('event thresholds:' \
                + Fore.RED + ' port side={:>5.2f}; port={:>5.2f};'.format(self._port_side_trigger_distance, self._port_trigger_distance) \
                + Fore.BLUE + ' center={:>5.2f};'.format(self._center_trigger_distance) \
                + Fore.GREEN + ' stbd={:>5.2f}; stbd side={:>5.2f}'.format(self._stbd_trigger_distance, self._stbd_side_trigger_distance ))
        # long distance:
        self._port_side_trigger_distance_far = self._config.get('port_side_trigger_distance_far')
        self._port_trigger_distance_far      = self._config.get('port_trigger_distance_far')
        self._center_trigger_distance_far    = self._config.get('center_trigger_distance_far')
        self._stbd_trigger_distance_far      = self._config.get('stbd_trigger_distance_far')
        self._stbd_side_trigger_distance_far = self._config.get('stbd_side_trigger_distance_far')
        self._log.info('long distance event thresholds:' \
                + Fore.RED + ' port side={:>5.2f}; port={:>5.2f};'.format(self._port_side_trigger_distance_far, self._port_trigger_distance_far) \
                + Fore.BLUE + ' center={:>5.2f};'.format(self._center_trigger_distance_far) \
                + Fore.GREEN + ' stbd={:>5.2f}; stbd side={:>5.2f}'.format(self._stbd_trigger_distance_far, self._stbd_side_trigger_distance_far ))
        self._loop_delay_sec = self._config.get('loop_delay_sec')
        self._log.debug('initialising integrated front sensor...')
        self._counter = itertools.count()
        self._last_event = None
        self._thread  = None
        self._enabled = False
        self._suppressed = False
        self._closing = False
        self._closed  = False
        self._ioe = IoExpander(config, Level.INFO)
        self._log.info('ready.')

    # ..........................................................................
    def _callback(self, pin, pin_type, value):
        '''
            This is the callback method from the I²C Master, whose events are
            being returned from the Arduino.

            The pin designations for each sensor are hard-coded to match the 
            robot's hardware as well as the Arduino. There's little point in 
            configuring this in the YAML since it's hard-coded in both hardware
            and software. The default pins A1-A5 are defined as IR analog 
            sensors, 9-11 are digital bumper sensors.
        '''
        if not self._enabled or self._suppressed:
            self._log.debug(Fore.BLACK + Style.DIM + 'SUPPRESSED callback: pin {:d}; type: {}; value: {:d}'.format(pin, pin_type, value))
            return
#       self._log.debug(Fore.BLACK + Style.BRIGHT + 'callback: pin {:d}; type: {}; value: {:d}'.format(pin, pin_type, value))
        _message = None
        # NOTE: the shorter range infrared triggers preclude the longer range triggers 
        if pin == self._port_side_ir_pin:
            if value > self._port_side_trigger_distance:
                _message = Message(Event.INFRARED_PORT_SIDE)
            elif value > self._port_side_trigger_distance_far:
                _message = Message(Event.INFRARED_PORT_SIDE)
        elif pin == self._port_ir_pin:
            if value > self._port_trigger_distance:
                _message = Message(Event.INFRARED_PORT)
            elif value > self._port_trigger_distance_far:
                _message = Message(Event.INFRARED_PORT_FAR)
        elif pin == self._center_ir_pin:
            if value > self._center_trigger_distance:
                _message = Message(Event.INFRARED_CNTR)
            elif value > self._center_trigger_distance_far:
                _message = Message(Event.INFRARED_CNTR_FAR)
        elif pin == self._stbd_ir_pin:
            if value > self._stbd_trigger_distance:
                _message = Message(Event.INFRARED_STBD)
            elif value > self._stbd_trigger_distance_far:
                _message = Message(Event.INFRARED_STBD_FAR)
        elif pin == 5: #self._stbd_side_ir_pin:
            if value > self._stbd_side_trigger_distance:
                _message = Message(Event.INFRARED_STBD_SIDE)
            elif value > self._stbd_side_trigger_distance_far:
                _message = Message(Event.INFRARED_STBD_SIDE_FAR)
        elif pin == self._port_bmp_pin:
            if value == 1:
                _message = Message(Event.BUMPER_PORT)
        elif pin == self._center_bmp_pin:
            if value == 1:
                _message = Message(Event.BUMPER_CNTR)
        elif pin == self._stbd_bmp_pin:
            if value == 1:
                _message = Message(Event.BUMPER_STBD)
        if _message is not None:
            _message.set_value(value)
            _event = _message.get_event()
            if not self._ignore_duplicates or _event != self._last_event:
                self._log.debug(Fore.CYAN + Style.BRIGHT + 'adding new message for event {}'.format(_event.description))
                self._queue.add(_message)
            else:
                self._log.info(Fore.CYAN + Style.DIM    + 'ignoring message for event {}'.format(_event.description))
                self._queue.add(_message) # FIXME remove this
            self._last_event = _event

    # ..........................................................................
    def suppress(self, state):
        self._log.info('suppress {}.'.format(state))
        self._suppressed = state

    # ..........................................................................
    def enable(self):
        if not self._enabled:
            if not self._closed:
                self._log.info('enabled integrated front sensor.')
                self._enabled = True
                if not self.in_loop():
                    self._start_front_sensor_loop()
                else:
                    self._log.error('cannot start integrated front sensor: already in loop.')
            else:
                self._log.warning('cannot enable integrated front sensor: already closed.')
        else:
            self._log.warning('already enabled integrated front sensor.')

    # ..........................................................................
    def in_loop(self):
        '''
            Returns true if the main loop is active (the thread is alive).
        '''
        return self._thread != None and self._thread.is_alive()

    # ..........................................................................
    def _front_sensor_loop(self):
        self._log.info('starting event loop...\n')

        while self._enabled:
            _count = next(self._counter)

            _start_time = dt.datetime.now()

            _port_side_data = self.get_input_for_event_type(Event.INFRARED_PORT_SIDE)
            _port_data      = self.get_input_for_event_type(Event.INFRARED_PORT)
            _cntr_data      = self.get_input_for_event_type(Event.INFRARED_CNTR)
            _stbd_data      = self.get_input_for_event_type(Event.INFRARED_STBD)
            _stbd_side_data = self.get_input_for_event_type(Event.INFRARED_STBD_SIDE)
            _port_bmp_data  = self.get_input_for_event_type(Event.BUMPER_PORT)
            _cntr_bmp_data  = self.get_input_for_event_type(Event.BUMPER_CNTR)
            _stbd_bmp_data  = self.get_input_for_event_type(Event.BUMPER_STBD)

            _delta = dt.datetime.now() - _start_time
            _elapsed_ms = int(_delta.total_seconds() * 1000) 
            # typically 173ms from ItsyBitsy, 85ms from Pimoroni IO Expander

            self._log.debug( Fore.WHITE + '[{:04d}] elapsed: {:d}ms'.format(_count, _elapsed_ms))

            # pin 1: analog infrared sensor ................
            self._log.debug('[{:04d}] ANALOG IR ({:d}):       \t'.format(_count, 1) + ( Fore.RED if ( _port_side_data > 100.0 ) else Fore.YELLOW ) \
                    + Style.BRIGHT + '{:d}'.format(_port_side_data) + Style.DIM + '\t(analog value 0-255)')
            self._callback(1, PinType.ANALOG_INPUT, _port_side_data)

            # pin 2: analog infrared sensor ................
            self._log.debug('[{:04d}] ANALOG IR ({:d}):       \t'.format(_count, 2) + ( Fore.RED if ( _port_data > 100.0 ) else Fore.YELLOW ) \
                    + Style.BRIGHT + '{:d}'.format(_port_data) + Style.DIM + '\t(analog value 0-255)')
            self._callback(2, PinType.ANALOG_INPUT, _port_data)

            # pin 3: analog infrared sensor ................
            self._log.debug('[{:04d}] ANALOG IR ({:d}):       \t'.format(_count, 3) + ( Fore.RED if ( _cntr_data > 100.0 ) else Fore.YELLOW ) \
                    + Style.BRIGHT + '{:d}'.format(_cntr_data) + Style.DIM + '\t(analog value 0-255)')
            self._callback(3, PinType.ANALOG_INPUT, _cntr_data)

            # pin 4: analog infrared sensor ................
            self._log.debug('[{:04d}] ANALOG IR ({:d}):       \t'.format(_count, 4) + ( Fore.RED if ( _stbd_data > 100.0 ) else Fore.YELLOW ) \
                    + Style.BRIGHT + '{:d}'.format(_stbd_data) + Style.DIM + '\t(analog value 0-255)')
            self._callback(4, PinType.ANALOG_INPUT, _stbd_data)

            # pin 5: analog infrared sensor ................
            self._log.debug('[{:04d}] ANALOG IR ({:d}):       \t'.format(_count, 5) + ( Fore.RED if ( _stbd_side_data > 100.0 ) else Fore.YELLOW ) \
                    + Style.BRIGHT + '{:d}'.format(_stbd_side_data) + Style.DIM + '\t(analog value 0-255)')
            self._callback(5, PinType.ANALOG_INPUT, _stbd_side_data)

            # pin 9: digital bumper sensor .................
            self._log.debug('[{:04d}] DIGITAL IR ({:d}):      \t'.format(_count, 9) + Fore.GREEN + Style.BRIGHT  + '{:d}'.format(_port_bmp_data) \
                    + Style.DIM + '\t(displays digital pup value 0|1)')
            self._callback(9, PinType.DIGITAL_INPUT_PULLUP, _port_bmp_data)

            # pin 10: digital bumper sensor ................
            self._log.debug('[{:04d}] DIGITAL IR ({:d}):      \t'.format(_count, 10) + Fore.GREEN + Style.BRIGHT  + '{:d}'.format(_cntr_bmp_data) \
                    + Style.DIM + '\t(displays digital pup value 0|1)')
            self._callback(10, PinType.DIGITAL_INPUT_PULLUP, _cntr_bmp_data)

            # pin 11: digital bumper sensor ................
            self._log.debug('[{:04d}] DIGITAL IR ({:d}):      \t'.format(_count, 11) + Fore.GREEN + Style.BRIGHT  + '{:d}'.format(_stbd_bmp_data) \
                    + Style.DIM + '\t(displays digital pup value 0|1)')
            self._callback(11, PinType.DIGITAL_INPUT_PULLUP, _stbd_bmp_data)

            time.sleep(self._loop_delay_sec)

        self._log.info('exited event loop.')

    # ..........................................................................
    def _start_front_sensor_loop(self):
        '''
            This is the method to call to actually start the loop.
        '''
        if not self._enabled:
            raise Exception('attempt to start front sensor event loop while disabled.')
        elif not self._closed:
            if self._thread is None:
                self._thread = threading.Thread(target=IntegratedFrontSensor._front_sensor_loop, args=[self])
                self._thread.start()
                self._log.info('started.')
            else:
                self._log.warning('cannot enable: process already running.')
        else:
            self._log.warning('cannot enable: already closed.')

    # ..........................................................................
    def get_input_for_event_type(self, event):
        '''
            Return the current value of the pin corresponding to the Event type.
        '''
        if event is Event.INFRARED_PORT_SIDE or event is Event.INFRARED_PORT_SIDE_FAR:
            return self._ioe.get_port_side_ir_value() 
        elif event is Event.INFRARED_PORT or event is Event.INFRARED_PORT_FAR:
            return self._ioe.get_port_ir_value()      
        elif event is Event.INFRARED_CNTR or event is Event.INFRARED_CNTR_FAR:
            return self._ioe.get_center_ir_value()    
        elif event is Event.INFRARED_STBD or event is Event.INFRARED_STBD_FAR:
            return self._ioe.get_stbd_ir_value()      
        elif event is Event.INFRARED_STBD_SIDE or event is Event.INFRARED_STBD_SIDE_FAR:
            return self._ioe.get_stbd_side_ir_value() 
        elif event is Event.BUMPER_PORT:
            return self._ioe.get_port_bmp_value()     
        elif event is Event.BUMPER_CNTR:
            return self._ioe.get_center_bmp_value()   
        elif event is Event.BUMPER_STBD:
            return self._ioe.get_stbd_bmp_value()     
        else:
            raise Exception('unexpected event type.')

    # ..........................................................................
    def disable(self):
        self._log.info('disabled integrated front sensor.')
        self._enabled = False

    # ..........................................................................
    def close(self):
        '''
            Permanently close and disable the integrated front sensor.
        '''
        if self._closing:
            self._log.info('already closing front sensor.')
            return
        if not self._closed:
            self._closing = True
            self._log.info('closing...')
            try:
                self._enabled = False
                if self._thread != None:
                    self._thread.join(timeout=1.0)
                    self._log.debug('front sensor loop thread joined.')
                    self._thread = None
                self._closed = True
#               self._pi.i2c_close(self._handle) # close device
                self._log.info('closed.')
            except Exception as e:
                self._log.error('error closing: {}'.format(e))
        else:
            self._log.debug('already closed.')


## main .........................................................................
#def main(argv):
#
#    try:
#
#        # read YAML configuration
#        _loader = ConfigLoader(Level.INFO)
#        filename = 'config.yaml'
#        _config = _loader.configure(filename)
#
#        _queue = MockMessageQueue(Level.INFO)
#
#        _ifs = IntegratedFrontSensor(_config, _queue, Level.INFO)
#        _board = _ioe.board
##       sys.exit(0)
#
##       _indicator = Indicator(Level.INFO)
##       # add indicator as message consumer
##       _queue.add_consumer(_indicator)
#
#        _max_value = 0
#
#        # start...
#        while True:
#
#            _start_time = dt.datetime.now()
#
#            _port_side_ir_value = _ioe.get_port_side_ir_value()
#            _port_ir_value      = _ioe.get_port_ir_value()
#            _center_ir_value    = _ioe.get_center_ir_value()
#            _stbd_ir_value      = _ioe.get_stbd_ir_value()
#            _stbd_side_ir_value = _ioe.get_stbd_side_ir_value()
#            _port_bmp_value     = _ioe.get_port_bmp_value()
#            _center_bmp_value   = _ioe.get_center_bmp_value()
#            _stbd_bmp_value     = _ioe.get_stbd_bmp_value()
#
##           _port_side_ir_value = _board.input(_ioe._port_side_ir_pin )
##           _max_value = max(_max_value, _port_side_ir_value)
##           _port_ir_value      = _board.input(_ioe._port_ir_pin)
##           _max_value = max(_max_value, _port_ir_value)
##           _center_ir_value    = _board.input(_ioe._center_ir_pin)
##           _max_value = max(_max_value, _center_ir_value)
##           _stbd_ir_value      = _board.input(_ioe._stbd_ir_pin)
##           _max_value = max(_max_value, _stbd_ir_value)
##           _stbd_side_ir_value = _board.input(_ioe._stbd_side_ir_pin)
##           _max_value = max(_max_value, _stbd_side_ir_value)
##           _port_bmp_value     = _board.input(_ioe._port_bmp_pin) == 0
##           _max_value = max(_max_value, _port_bmp_value)
##           _center_bmp_value   = _board.input(_ioe._center_bmp_pin) == 0
##           _max_value = max(_max_value, _center_bmp_value)
##           _stbd_bmp_value     = _board.input(_ioe._stbd_bmp_pin) == 0
##           _max_value = max(_max_value, _stbd_bmp_value)
#
#            _delta = dt.datetime.now() - _start_time
#            _elapsed_ms = int(_delta.total_seconds() * 1000)
#
#            print(Fore.RED       + 'PSIR: {:d}; '.format(_port_side_ir_value) \
#                  + Fore.MAGENTA + 'PIR: {:d}; '.format(_port_ir_value) \
#                  + Fore.BLUE    + 'CIR: {:d}; '.format(_center_ir_value) \
#                  + Fore.CYAN    + 'SIR: {:d}; '.format(_stbd_ir_value) \
#                  + Fore.GREEN   + 'SSIR: {:d} '.format(_stbd_side_ir_value) \
#                  + Fore.MAGENTA + 'PB: {}; '.format(_port_bmp_value) \
#                  + Fore.BLUE    + 'CB: {}; '.format(_center_bmp_value) \
#                  + Fore.CYAN    + 'SB: {}; '.format(_stbd_bmp_value) \
#                  + Fore.BLACK   + 'max: {:>5.2f}; '.format(_max_value) \
#                  + Fore.WHITE   + '{:>5.2f}ms elapsed.'.format(_elapsed_ms) + Style.RESET_ALL)
#
##           time.sleep(1.0 / 30)
#
#
#    except KeyboardInterrupt:
#        print(Fore.CYAN + Style.BRIGHT + 'caught Ctrl-C; exiting...')
#        
#    except Exception:
#        print(Fore.RED + Style.BRIGHT + 'error starting IoExpander: {}'.format(traceback.format_exc()) + Style.RESET_ALL)
#
## call main ....................................................................
#if __name__== "__main__":
#    main(sys.argv[1:])

#EOF
