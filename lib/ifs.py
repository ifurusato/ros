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
import numpy as np
import datetime as dt
from collections import deque as Deque
from colorama import init, Fore, Style
init()

import ioexpander as io

from lib.config_loader import ConfigLoader
from lib.pintype import PinType
from lib.logger import Logger, Level
from lib.enums import Orientation
from lib.event import Event
from lib.message import Message, MessageFactory
from lib.indicator import Indicator
#from lib.pot import Potentiometer # for calibration only


# ..............................................................................
class MockMessageQueue():
    '''
        This message queue waits for at least one infrared event of each type.
    '''

    def __init__(self, level):
        super().__init__()
        self._message_counter = itertools.count()
        self._log = Logger("mock queue", Level.INFO)
        self._log.info('ready.')

    # ......................................................
    def add(self, message):
        message.set_number(next(self._message_counter))
        self._log.debug('added message #{}: priority {}: {}'.format(message.get_number(), message.get_priority(), message.get_description()))
        event = message.get_event()
        if event is Event.INFRARED_PORT_SIDE:
            self._log.debug(Fore.RED + Style.BRIGHT + 'INFRARED_PORT_SIDE: {}'.format(event.description))

        elif event is Event.INFRARED_PORT:
            self._log.debug(Fore.MAGENTA + Style.BRIGHT + 'INFRARED_PORT: {}'.format(event.description))

        elif event is Event.INFRARED_CNTR:
            self._log.debug(Fore.BLUE + Style.BRIGHT + 'INFRARED_CNTR: {}'.format(event.description))

        elif event is Event.INFRARED_STBD:
            self._log.debug(Fore.CYAN + Style.BRIGHT + 'INFRARED_STBD: {}'.format(event.description))

        elif event is Event.INFRARED_STBD_SIDE:
            self._log.debug(Fore.GREEN + Style.BRIGHT + 'INFRARED_STBD_SIDE: {}'.format(event.description))

        elif event is Event.BUMPER_PORT:
            self._log.debug(Fore.RED + Style.BRIGHT + 'BUMPER_PORT: {}'.format(event.description))
        elif event is Event.BUMPER_CNTR:
            self._log.debug(Fore.BLUE + Style.BRIGHT + 'BUMPER_CNTR: {}'.format(event.description))
        elif event is Event.BUMPER_STBD:
            self._log.debug(Fore.GREEN + Style.BRIGHT + 'BUMPER_STBD: {}'.format(event.description))
        else:
            self._log.debug(Fore.BLACK + Style.BRIGHT + 'other event: {}'.format(event.description))

#   # ......................................................
#   def is_complete(self):
#       return not self._events

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
        self._port_side_ir_pin = _config.get('port_side_ir_pin')  # pin connected to port side infrared
        self._port_ir_pin      = _config.get('port_ir_pin')       # pin connected to port infrared
        self._center_ir_pin    = _config.get('center_ir_pin')     # pin connected to center infrared
        self._stbd_ir_pin      = _config.get('stbd_ir_pin')       # pin connected to starboard infrared
        self._stbd_side_ir_pin = _config.get('stbd_side_ir_pin')  # pin connected to starboard side infrared
        self._log.info('IR pin assignments: port side: {:d}; port: {:d}; center: {:d}; stbd: {:d}; stbd side: {:d}.'.format(\
                self._port_side_ir_pin, self._port_ir_pin, self._center_ir_pin, self._stbd_ir_pin, self._stbd_side_ir_pin))
        # bumpers
        self._port_bmp_pin     = _config.get('port_bmp_pin')      # pin connected to port bumper
        self._center_bmp_pin   = _config.get('center_bmp_pin')    # pin connected to center bumper
        self._stbd_bmp_pin     = _config.get('stbd_bmp_pin')      # pin connected to starboard bumper
        self._log.info('BMP pin assignments: port: {:d}; center: {:d}; stbd: {:d}.'.format(\
                self._port_ir_pin, self._center_ir_pin, self._stbd_ir_pin))

        # configure board
        self._ioe = io.IOE(i2c_addr=0x18)
        self.board = self._ioe  # TEMP
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
        return int(round(self._ioe.input(self._port_side_ir_pin) * 100.0))

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
           message_factory: optional MessageFactory
           level:  the logging Level
    
        Usage:
    
           _ifs = IntegratedFrontSensor(_config, _queue, Level.INFO)
           _ifs.enable()
    '''

    # ..........................................................................
    def __init__(self, config, queue, message_factory, level):
        if config is None:
            raise ValueError('no configuration provided.')
        _cruise_config = config['ros'].get('cruise_behaviour')
        self._cruising_velocity = _cruise_config.get('cruising_velocity')
        self._config = config['ros'].get('integrated_front_sensor')
        self._queue = queue
        self._log = Logger("ifs", level)
        self._device_id = self._config.get('device_id')  # i2c hex address of slave device, must match Arduino's SLAVE_I2C_ADDRESS
        self._channel = self._config.get('channel')
        self._ignore_duplicates = False  # TODO set from config
        # hardware pin assignments
        self._port_side_ir_pin = self._config.get('port_side_ir_pin')
        self._port_ir_pin      = self._config.get('port_ir_pin')
        self._center_ir_pin    = self._config.get('center_ir_pin')
        self._stbd_ir_pin      = self._config.get('stbd_ir_pin')
        self._stbd_side_ir_pin = self._config.get('stbd_side_ir_pin')
        self._port_bmp_pin     = self._config.get('port_bmp_pin')
        self._center_bmp_pin   = self._config.get('center_bmp_pin')
        self._stbd_bmp_pin     = self._config.get('stbd_bmp_pin')
        # short distance:
        self._port_side_trigger_distance = self._config.get('port_side_trigger_distance')
        self._port_trigger_distance      = self._config.get('port_trigger_distance')
        self._center_trigger_distance    = self._config.get('center_trigger_distance')
        self._stbd_trigger_distance      = self._config.get('stbd_trigger_distance')
        self._stbd_side_trigger_distance = self._config.get('stbd_side_trigger_distance')
        self._log.info('event thresholds:' \
                +Fore.RED + ' port side={:>5.2f}; port={:>5.2f};'.format(self._port_side_trigger_distance, self._port_trigger_distance) \
                +Fore.BLUE + ' center={:>5.2f};'.format(self._center_trigger_distance) \
                +Fore.GREEN + ' stbd={:>5.2f}; stbd side={:>5.2f}'.format(self._stbd_trigger_distance, self._stbd_side_trigger_distance))
        self._loop_delay_sec = self._config.get('loop_delay_sec')
        if message_factory:
            self._message_factory = message_factory
        else:
            self._message_factory = MessageFactory(level)
        self._log.debug('initialising integrated front sensor...')
        self._loop_counter = itertools.count()
        self._callback_counter = itertools.count()
        self._callback_count = 0
        self._last_event = None
        self._thread = None
        self._enabled = False
        self._suppressed = False
        self._closing = False
        self._closed = False
        self._N         = 0     # TEMP mean count
        self._avg       = 0
        self._ioe = IoExpander(config, Level.INFO)
        # calculating means for IR sensors
#       self._pot = Potentiometer(config, Level.INFO) # TEMP
        _queue_limit = 10
        self._deque_port_side = Deque([], maxlen=_queue_limit)
        self._deque_port      = Deque([], maxlen=_queue_limit)
        self._deque_cntr      = Deque([], maxlen=_queue_limit)
        self._deque_stbd      = Deque([], maxlen=_queue_limit)
        self._deque_stbd_side = Deque([], maxlen=_queue_limit)
        # ...
        self._log.info('ready.')

    # ..........................................................................
    def _get_mean_distance(self, orientation, value): 
        '''
           Returns the mean of values collected in the queue for the specified IR sensor.
        '''
        if orientation is Orientation.PORT_SIDE:
            _queue = self._deque_port_side 
        elif orientation is Orientation.PORT:
            _queue = self._deque_port     
        elif orientation is Orientation.CNTR:
            _queue = self._deque_cntr
        elif orientation is Orientation.STBD:
            _queue = self._deque_stbd    
        elif orientation is Orientation.STBD_SIDE:
            _queue = self._deque_stbd_side
        else:
            raise ValueError('unsupported orientation.')
        _queue.append(value)
        _n = 0
        _mean = 0.0
        for x in _queue:
            _n += 1
            _mean += ( x - _mean ) / _n
        if _n < 1:
            return float('nan');
        else:
            return _mean

    # ..........................................................................
    def get_mean_distance(self, orientation): 
        '''
           Returns the mean of the most recent values collected in the queue for the specified IR sensor.
           If the queue is empty returns -1.
        '''
        if orientation is Orientation.PORT_SIDE:
            _queue = self._deque_port_side 
        elif orientation is Orientation.PORT:
            _queue = self._deque_port     
        elif orientation is Orientation.CNTR:
            _queue = self._deque_cntr
        elif orientation is Orientation.STBD:
            _queue = self._deque_stbd    
        elif orientation is Orientation.STBD_SIDE:
            _queue = self._deque_stbd_side
        else:
            raise ValueError('unsupported orientation.')
        if len(_queue) > 0:
            _n = 0
            _mean = 0.0
            for x in _queue:
                _n += 1
                _mean += ( x - _mean ) / _n
            if _n < 1:
                return float('nan');
            else:
                return _mean
        else:
            return -1.0

    # ..........................................................................
    def _convert_to_distance(self, value):
        '''
            Converts the value returned by the IR sensor to a distance in centimeters.
       
            Distance Calculation ---------------

            This is reading the distance from a 3 volt Sharp GP2Y0A60SZLF infrared 
            sensor to a piece of white A4 printer paper in a low ambient light room. 
            The sensor output is not linear, but its accuracy is not critical. If 
            the target is too close to the sensor the values are not valid. According 
            to spec 10cm is the minimum distance, but we get relative variability up 
            until about 5cm. Values over 150 clearly indicate the robot is less than 
            10cm from the target.
 
                0cm = unreliable
                5cm = 226.5
              7.5cm = 197.0
               10cm = 151.0
               20cm =  92.0
               30cm =  69.9
               40cm =  59.2
               50cm =  52.0
               60cm =  46.0
               70cm =  41.8
               80cm =  38.2
               90cm =  35.8
              100cm =  34.0
              110cm =  32.9
              120cm =  31.7
              130cm =  30.7 *
              140cm =  30.7 *
              150cm =  29.4 *

            * Maximum range on IR is about 130cm, after which there is diminishing 
              stability/variability, i.e., it's hard to determine if we're dealing
              with a level of system noise rather than data. Different runs produce
              different results, with values between 28 - 31 on a range of any more 
              than 130cm.

           See: http://ediy.com.my/blog/item/92-sharp-gp2y0a21-ir-distance-sensors
        '''
#       _pot_value = self._pot.get_scaled_value()
#       EXPONENT = _pot_value
        EXPONENT = 1.37
        _distance = pow( 900.0 / value, EXPONENT )
#       self._log.info(Fore.BLACK + Style.NORMAL + 'value: {:>5.2f}; pot value: {:>5.2f}; distance: {:>5.2f}cm'.format(value, _pot_value, _distance))
        return _distance

    # ..........................................................................
    def _callback(self, pin, pin_type, value):
        '''
            This is the callback method from the I²C Master, whose events are
            being returned from the source, e.g., Arduino or IO Expander board.
        '''
        if not self._enabled or self._suppressed:
            self._log.debug(Fore.BLACK + Style.DIM + 'SUPPRESSED callback: pin {:d}; type: {}; value: {:d}'.format(pin, pin_type, value))
            return
        self._log.debug('callback: pin {:d}; type: {}; value: {:d}'.format(pin, pin_type, value))
        _event = None

        # ..........................................................................................
        # for IR sensors we rewrite the value with a dynamic mean distance (cm), 
        # setting the event type only if the value is less than a distance threshold
        if pin == self._port_side_ir_pin:
            value = self._get_mean_distance(Orientation.PORT_SIDE, self._convert_to_distance(value))
            if value < self._port_side_trigger_distance:
                self._log.info(Fore.RED + '{:d} mean distance: {:5.2f}cm; PORT SIDE'.format(self._callback_count, value))
                _event = Event.INFRARED_PORT_SIDE

        elif pin == self._port_ir_pin:
            value = self._get_mean_distance(Orientation.PORT, self._convert_to_distance(value))
            if value < self._port_trigger_distance:
                self._log.info(Fore.RED + '{:d} mean distance: {:5.2f}cm; PORT'.format(self._callback_count, value))
                _event = Event.INFRARED_PORT

        elif pin == self._center_ir_pin:
            value = self._get_mean_distance(Orientation.CNTR, self._convert_to_distance(value))
            if value < self._center_trigger_distance:
                self._log.info(Fore.BLUE + '{:d} mean distance: {:5.2f}cm; CNTR'.format(self._callback_count, value))
                _event = Event.INFRARED_CNTR

        elif pin == self._stbd_ir_pin:
            value = self._get_mean_distance(Orientation.STBD, self._convert_to_distance(value))
            if value < self._stbd_trigger_distance:
                self._log.info(Fore.GREEN + '{:d} mean distance: {:5.2f}cm; STBD'.format(self._callback_count, value))
                _event = Event.INFRARED_STBD

        elif pin == self._stbd_side_ir_pin:
            value = self._get_mean_distance(Orientation.STBD_SIDE, self._convert_to_distance(value))
            if value < self._stbd_side_trigger_distance:
                self._log.info(Fore.GREEN + '{:d} mean distance: {:5.2f}cm; STBD SIDE'.format(self._callback_count, value))
                _event = Event.INFRARED_STBD_SIDE
        # ..........................................................................................

        elif pin == self._port_bmp_pin:
            if value == 1:
                _event = Event.BUMPER_PORT
        elif pin == self._center_bmp_pin:
            if value == 1:
                _event = Event.BUMPER_CNTR
        elif pin == self._stbd_bmp_pin:
            if value == 1:
                _event = Event.BUMPER_STBD
        if _event is not None:
            self._callback_count = next(self._callback_counter)
            self._log.debug(Fore.GREEN + '{:d} callbacks.'.format(self._callback_count))
            if not self._ignore_duplicates or _event != self._last_event:
                _message = self._message_factory.get_message(_event, value)
                self._log.debug(Fore.CYAN + Style.BRIGHT + 'adding new message eid#{} for event {}'.format(_message.eid, _event.description))
                self._queue.add(_message)
            else:
                self._log.warning(Fore.CYAN + Style.NORMAL + 'ignoring message for event {}'.format(_event.description))
            self._last_event = _event

    # ..........................................................................
    @staticmethod
    def clamp(n, minn, maxn):
        return max(min(maxn, n), minn)


    # ..........................................................................
    @staticmethod
    def remap(x, in_min, in_max, out_min, out_max):
        return (x - in_min) * (out_max - out_min) / (in_max - in_min) + out_min


    # ..........................................................................
    def in_loop(self):
        '''
            Returns true if the main loop is active (the thread is alive).
        '''
        return self._thread != None and self._thread.is_alive()

    # ..........................................................................
    def __loop(self):
        self._log.info('starting event loop...\n')

        while self._enabled:
            _count = next(self._loop_counter)
#           self._log.info(Fore.WHITE + Style.DIM + '[{:04d}] loop start.'.format(_count))
            _start_time = dt.datetime.now()

            _port_side_data = self.get_input_for_event_type(Event.INFRARED_PORT_SIDE)
            _port_data = self.get_input_for_event_type(Event.INFRARED_PORT)
            _cntr_data = self.get_input_for_event_type(Event.INFRARED_CNTR)
            _stbd_data = self.get_input_for_event_type(Event.INFRARED_STBD)
            _stbd_side_data = self.get_input_for_event_type(Event.INFRARED_STBD_SIDE)
            _port_bmp_data = self.get_input_for_event_type(Event.BUMPER_PORT)
            _cntr_bmp_data = self.get_input_for_event_type(Event.BUMPER_CNTR)
            _stbd_bmp_data = self.get_input_for_event_type(Event.BUMPER_STBD)

            _delta = dt.datetime.now() - _start_time
            _elapsed_ms = int(_delta.total_seconds() * 1000) 
            # typically 173ms from ItsyBitsy, 85ms from Pimoroni IO Expander
            self._log.debug(Fore.WHITE + '[{:04d}] acquisition time elapsed: {:d}ms'.format(_count, _elapsed_ms))

            # pin 1: analog infrared sensor ................
            self._log.debug('[{:04d}] ANALOG IR ({:d}):       \t'.format(_count, 1) + (Fore.RED if (_port_side_data > 100.0) else Fore.YELLOW) \
                    +Style.BRIGHT + '{:d}'.format(_port_side_data) + Style.DIM + '\t(analog value 0-255)')
            self._callback(1, PinType.ANALOG_INPUT, _port_side_data)

            # pin 2: analog infrared sensor ................
            self._log.debug('[{:04d}] ANALOG IR ({:d}):       \t'.format(_count, 2) + (Fore.RED if (_port_data > 100.0) else Fore.YELLOW) \
                    +Style.BRIGHT + '{:d}'.format(_port_data) + Style.DIM + '\t(analog value 0-255)')
            self._callback(2, PinType.ANALOG_INPUT, _port_data)

            # pin 3: analog infrared sensor ................
            self._log.debug('[{:04d}] ANALOG IR ({:d}):       \t'.format(_count, 3) + (Fore.RED if (_cntr_data > 100.0) else Fore.YELLOW) \
                    +Style.BRIGHT + '{:d}'.format(_cntr_data) + Style.DIM + '\t(analog value 0-255)')
            self._callback(3, PinType.ANALOG_INPUT, _cntr_data)

            # pin 4: analog infrared sensor ................
            self._log.debug('[{:04d}] ANALOG IR ({:d}):       \t'.format(_count, 4) + (Fore.RED if (_stbd_data > 100.0) else Fore.YELLOW) \
                    +Style.BRIGHT + '{:d}'.format(_stbd_data) + Style.DIM + '\t(analog value 0-255)')
            self._callback(4, PinType.ANALOG_INPUT, _stbd_data)

            # pin 5: analog infrared sensor ................
            self._log.debug('[{:04d}] ANALOG IR ({:d}):       \t'.format(_count, 5) + (Fore.RED if (_stbd_side_data > 100.0) else Fore.YELLOW) \
                    +Style.BRIGHT + '{:d}'.format(_stbd_side_data) + Style.DIM + '\t(analog value 0-255)')
            self._callback(5, PinType.ANALOG_INPUT, _stbd_side_data)

            # pin 9: digital bumper sensor .................
            self._log.debug('[{:04d}] DIGITAL IR ({:d}):      \t'.format(_count, 9) + Fore.GREEN + Style.BRIGHT + '{:d}'.format(_port_bmp_data) \
                    +Style.DIM + '\t(displays digital pup value 0|1)')
            self._callback(9, PinType.DIGITAL_INPUT_PULLUP, _port_bmp_data)

            # pin 10: digital bumper sensor ................
            self._log.debug('[{:04d}] DIGITAL IR ({:d}):      \t'.format(_count, 10) + Fore.GREEN + Style.BRIGHT + '{:d}'.format(_cntr_bmp_data) \
                    +Style.DIM + '\t(displays digital pup value 0|1)')
            self._callback(10, PinType.DIGITAL_INPUT_PULLUP, _cntr_bmp_data)

            # pin 11: digital bumper sensor ................
            self._log.debug('[{:04d}] DIGITAL IR ({:d}):      \t'.format(_count, 11) + Fore.GREEN + Style.BRIGHT + '{:d}'.format(_stbd_bmp_data) \
                    +Style.DIM + '\t(displays digital pup value 0|1)')
            self._callback(11, PinType.DIGITAL_INPUT_PULLUP, _stbd_bmp_data)

#           self._log.info(Fore.WHITE + Style.DIM + '[{:04d}] loop end.'.format(_count))
            time.sleep(self._loop_delay_sec)

        self._log.info('exited event loop.')

    # ..........................................................................
    def _start_front_sensor_loop(self):
        '''
            This is the method to call to actually start the loop thread.
        '''
        if not self._enabled:
            raise Exception('attempt to start front sensor event loop while disabled.')
        elif not self._closed:
            if self._thread is None:
                self._thread = threading.Thread(target=IntegratedFrontSensor.__loop, args=[self])
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
        if event is Event.INFRARED_PORT_SIDE:
            return self._ioe.get_port_side_ir_value() 
        elif event is Event.INFRARED_PORT:
            return self._ioe.get_port_ir_value()      
        elif event is Event.INFRARED_CNTR:
            return self._ioe.get_center_ir_value()    
        elif event is Event.INFRARED_STBD:
            return self._ioe.get_stbd_ir_value()      
        elif event is Event.INFRARED_STBD_SIDE:
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

# EOF
