#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# Copyright 2020 by Murray Altheim. All rights reserved. This file is part of
# the Robot OS project and is released under the "Apache Licence, Version 2.0".
# Please see the LICENSE file included as part of this package.
#
# author:   altheim
# created:  2020-01-18
# modified: 2020-10-28
#
# Implements an Integrated Front Sensor using an IO Expander Breakout Garden
# board. This polls the values of the board's pins, which outputs 0-255 values
# for analog pins, and a 0 or 1 for digital pins.
#

from concurrent.futures import ThreadPoolExecutor #, ProcessPoolExecutor
import time, threading
import datetime as dt
from collections import deque as Deque
from colorama import init, Fore, Style
init()

import ioexpander as io

from lib.config_loader import ConfigLoader
from lib.logger import Logger, Level
from lib.enums import Orientation
from lib.event import Event
from lib.message_factory import MessageFactory
from lib.message_bus import MessageBus
from lib.message import Message
#from lib.indicator import Indicator
from lib.pot import Potentiometer # for calibration only


# ..............................................................................
class IntegratedFrontSensor():
    '''
    IntegratedFrontSensor: communicates with the integrated front bumpers and
    infrared sensors, receiving messages from the IO Expander board or I²C
    Arduino slave, sending the messages with its events onto the message bus.

    This listens to the Clock and at a frequency of ( TICK % tick_modulo )
    calls the _poll() method.

    Parameters:

        :param config:           the YAML based application configuration
        :param queue:            the message queue receiving activation notifications
        :param clock:            the clock providing the polling loop trigger
        :param message_bus:      the message bus to send event messages
        :param message_factory:  optional MessageFactory
        :param level:            the logging Level

    '''

    # ..........................................................................
    def __init__(self, config, queue, clock, message_bus, message_factory, level):
        if config is None:
            raise ValueError('no configuration provided.')
        self._log = Logger("ifs", level)
        self._log.info('configuring integrated front sensor...')
        _cruise_config = config['ros'].get('cruise_behaviour')
        self._cruising_velocity = _cruise_config.get('cruising_velocity')
        self._config = config['ros'].get('integrated_front_sensor')
        self._clock             = clock
        self._clock.add_consumer(self)
        self._message_bus       = message_bus
#       _queue = queue
#       _queue.add_consumer(self)
        self._device_id         = self._config.get('device_id') # i2c hex address of slave device, must match Arduino's SLAVE_I2C_ADDRESS
        self._channel           = self._config.get('channel')
        self._ignore_duplicates = self._config.get('ignore_duplicates')
        self._tick_modulo       = self._config.get('tick_modulo')
        _max_workers            = self._config.get('max_workers')
        self._log.info('tick modulo: {:d}'.format(self._tick_modulo) )
        # event thresholds:
        self._callback_cntr_min_trigger  = self._config.get('callback_center_minimum_trigger')
        self._callback_side_min_trigger  = self._config.get('callback_side_minimum_trigger')
        self._callback_min_trigger       = self._config.get('callback_minimum_trigger')
        self._port_side_trigger_distance = self._config.get('port_side_trigger_distance')
        self._port_trigger_distance      = self._config.get('port_trigger_distance')
        self._center_trigger_distance    = self._config.get('center_trigger_distance')
        self._stbd_trigger_distance      = self._config.get('stbd_trigger_distance')
        self._stbd_side_trigger_distance = self._config.get('stbd_side_trigger_distance')
        self._log.info('event thresholds:    \t' \
                +Fore.RED + ' port side={:>5.2f}; port={:>5.2f};'.format(self._port_side_trigger_distance, self._port_trigger_distance) \
                +Fore.BLUE + ' center={:>5.2f};'.format(self._center_trigger_distance) \
                +Fore.GREEN + ' stbd={:>5.2f}; stbd side={:>5.2f}'.format(self._stbd_trigger_distance, self._stbd_side_trigger_distance))
        # hardware pin assignments
        self._port_side_ir_pin  = self._config.get('port_side_ir_pin')
        self._port_ir_pin       = self._config.get('port_ir_pin')
        self._center_ir_pin     = self._config.get('center_ir_pin')
        self._stbd_ir_pin       = self._config.get('stbd_ir_pin')
        self._stbd_side_ir_pin  = self._config.get('stbd_side_ir_pin')
        self._log.info('infrared pin assignments:\t' \
                +Fore.RED + ' port side={:d}; port={:d};'.format(self._port_side_ir_pin, self._port_ir_pin) \
                +Fore.BLUE + ' center={:d};'.format(self._center_ir_pin) \
                +Fore.GREEN + ' stbd={:d}; stbd side={:d}'.format(self._stbd_ir_pin, self._stbd_side_ir_pin))
        self._port_bmp_pin      = self._config.get('port_bmp_pin')
        self._center_bmp_pin    = self._config.get('center_bmp_pin')
        self._stbd_bmp_pin      = self._config.get('stbd_bmp_pin')
        self._log.info('bumper pin assignments:\t' \
                +Fore.RED + ' port={:d};'.format(self._port_bmp_pin) \
                +Fore.BLUE + ' center={:d};'.format(self._center_bmp_pin) \
                +Fore.GREEN + ' stbd={:d}'.format(self._stbd_bmp_pin))
        if message_factory:
            self._message_factory = message_factory
        else:
            self._message_factory = MessageFactory(level)
#       self._executor = ProcessPoolExecutor(max_workers=_max_workers)
        self._log.info('creating thread pool executor with maximum of {:d} workers.'.format(_max_workers))
        self._executor = ThreadPoolExecutor(max_workers=_max_workers, thread_name_prefix='ifs')
        # config IO Expander
        self._ioe = IoExpander(config, Level.INFO)
        # calculating means for IR sensors
        self._pot = Potentiometer(config, Level.INFO)
        _queue_limit = 2 # larger number means it takes longer to change
        self._deque_port_side = Deque([], maxlen=_queue_limit)
        self._deque_port      = Deque([], maxlen=_queue_limit)
        self._deque_cntr      = Deque([], maxlen=_queue_limit)
        self._deque_stbd      = Deque([], maxlen=_queue_limit)
        self._deque_stbd_side = Deque([], maxlen=_queue_limit)
        # ...
        self._last_event = None
        self._last_value = None
        self._enabled    = False
        self._suppressed = False
        self._closed     = False
        self._log.info(Fore.MAGENTA + 'ready.')

    # ......................................................
    def add(self, message):
        '''
        Reacts to every nth (modulo) TICK message, submitting a _poll Thread
        from the thread pool executor, which polls the various sensors and
        sending callbacks for each.

        Note that if the loop frequency is set this method is disabled.
        '''
        if self._enabled and message.event is Event.CLOCK_TICK:
            if ( message.value % self._tick_modulo ) == 0:
                _future = self._executor.submit(self._poll, message.value, lambda: self.enabled )

    # ......................................................
    def _poll(self, count, f_is_enabled):
        '''
        Poll the various infrared and bumper sensors, executing callbacks for each.
        In tests this typically takes 173ms from ItsyBitsy, 85ms from the Pimoroni IO Expander.

        We add a messsage for the bumpers immediately (rather than use a callback) after reading
        the sensors since their response must be as fast as possible.
        '''
        if not f_is_enabled():
            self._log.warning('[{:04d}] poll not enabled'.format(count))
            return

        self._log.info(Fore.BLACK + '[{:04d}] ifs poll start.'.format(count))
        _current_thread = threading.current_thread()
        _current_thread.name = 'poll'
        _start_time = dt.datetime.now()

        # pin 10: digital bumper sensor ........................................
        _port_bmp_data     = self.get_input_for_event_type(Event.BUMPER_PORT)
        _cntr_bmp_data     = self.get_input_for_event_type(Event.BUMPER_CNTR)
        _stbd_bmp_data     = self.get_input_for_event_type(Event.BUMPER_STBD)

        _port_side_ir_data = self.get_input_for_event_type(Event.INFRARED_PORT_SIDE)
        _port_ir_data      = self.get_input_for_event_type(Event.INFRARED_PORT)
        _cntr_ir_data      = self.get_input_for_event_type(Event.INFRARED_CNTR)
        _stbd_ir_data      = self.get_input_for_event_type(Event.INFRARED_STBD)
        _stbd_side_ir_data = self.get_input_for_event_type(Event.INFRARED_STBD_SIDE)

#       self._callback(Event.BUMPER_CNTR, _cntr_bmp_data)
        if _cntr_bmp_data == 1:
            _message = self._message_factory.get_message(Event.BUMPER_CNTR, _cntr_bmp_data)
            self._log.info(Fore.BLUE + Style.BRIGHT + 'adding new message eid#{} for BUMPER_CNTR event.'.format(_message.eid))
            self._message_bus.handle(_message)

        # pin 9: digital bumper sensor .........................................
#       self._callback(Event.BUMPER_PORT, _port_bmp_data)
        if _port_bmp_data == 1:
            _message = self._message_factory.get_message(Event.BUMPER_PORT, _port_bmp_data)
            self._log.info(Fore.BLUE + Style.BRIGHT + 'adding new message eid#{} for BUMPER_PORT event.'.format(_message.eid))
            self._message_bus.handle(_message)

        # pin 11: digital bumper sensor ........................................
#       self._callback(Event.BUMPER_STBD, _stbd_bmp_data)
        if _stbd_bmp_data == 1:
            _message = self._message_factory.get_message(Event.BUMPER_STBD, _stbd_bmp_data)
            self._log.info(Fore.BLUE + Style.BRIGHT + 'adding new message eid#{} for BUMPER_STBD event.'.format(_message.eid))
            self._message_bus.handle(_message)

        # port side analog infrared sensor .....................................
        if _port_side_ir_data > self._callback_side_min_trigger:
#           _message = self._message_factory.get_message(Event.INFRARED_PORT_SIDE, _port_side_ir_data)
#           self._log.info(Fore.RED + Style.BRIGHT + 'adding new message eid#{} for INFRARED_PORT_SIDE event.'.format(_message.eid))
#           self._message_bus.handle(_message)
            self._log.info(Fore.RED + '[{:04d}] ANALOG IR ({:d}):       \t'.format(count, 1) + (Fore.RED if (_port_side_ir_data > 100.0) else Fore.YELLOW) \
                    + Style.BRIGHT + '{:d}'.format(_port_side_ir_data) + Style.DIM + '\t(analog value 0-255)')
            self._callback(Event.INFRARED_PORT_SIDE, _port_side_ir_data)

        # port analog infrared sensor ..........................................
        if _port_ir_data > self._callback_min_trigger:
#           _message = self._message_factory.get_message(Event.INFRARED_PORT, _port_ir_data)
#           self._log.info(Fore.RED + Style.BRIGHT + 'adding new message eid#{} for INFRARED_PORT event.'.format(_message.eid))
#           self._message_bus.handle(_message)
            self._log.info('[{:04d}] ANALOG IR ({:d}):       \t'.format(count, 2) + (Fore.RED if (_port_ir_data > 100.0) else Fore.YELLOW) \
                    + Style.BRIGHT + '{:d}'.format(_port_ir_data) + Style.DIM + '\t(analog value 0-255)')
            self._callback(Event.INFRARED_PORT, _port_ir_data)

        # center analog infrared sensor ........................................
        if _cntr_ir_data > self._callback_cntr_min_trigger:
#           _message = self._message_factory.get_message(Event.INFRARED_CNTR, _cntr_ir_data)
#           self._log.info(Fore.BLUE + Style.BRIGHT + 'adding new message eid#{} for INFRARED_CNTR event.'.format(_message.eid))
#           self._message_bus.handle(_message)
            self._log.info(Fore.BLUE + '[{:04d}] ANALOG IR ({:d}):       \t'.format(count, 3) + (Fore.RED if (_cntr_ir_data > 100.0) else Fore.YELLOW) \
                    + Style.BRIGHT + '{:d}'.format(_cntr_ir_data) + Style.DIM + '\t(analog value 0-255)')
            self._callback(Event.INFRARED_CNTR, _cntr_ir_data)

        # starboard analog infrared sensor .....................................
        if _stbd_ir_data > self._callback_min_trigger:
#           _message = self._message_factory.get_message(Event.INFRARED_STBD, _stbd_ir_data)
#           self._log.info(Fore.GREEN + Style.BRIGHT + 'adding new message eid#{} for INFRARED_STBD event.'.format(_message.eid))
#           self._message_bus.handle(_message)
            self._log.info('[{:04d}] ANALOG IR ({:d}):       \t'.format(count, 4) + (Fore.RED if (_stbd_ir_data > 100.0) else Fore.YELLOW) \
                    + Style.BRIGHT + '{:d}'.format(_stbd_ir_data) + Style.DIM + '\t(analog value 0-255)')
            self._callback(Event.INFRARED_STBD, _stbd_ir_data)

        # starboard side analog infrared sensor ................................
        if _stbd_side_ir_data > self._callback_side_min_trigger:
#           _message = self._message_factory.get_message(Event.INFRARED_STBD_SIDE, _stbd_side_ir_data)
#           self._log.info(Fore.GREEN + Style.BRIGHT + 'adding new message eid#{} for INFRARED_STBD_SIDE event.'.format(_message.eid))
#           self._message_bus.handle(_message)
            self._log.info('[{:04d}] ANALOG IR ({:d}):       \t'.format(count, 5) + (Fore.RED if (_stbd_side_ir_data > 100.0) else Fore.YELLOW) + Style.BRIGHT + '{:d}'.format(_stbd_side_ir_data) + Style.DIM + '\t(analog value 0-255)')
            self._callback(Event.INFRARED_STBD_SIDE, _stbd_side_ir_data)

        _delta = dt.datetime.now() - _start_time
        _elapsed_ms = int(_delta.total_seconds() * 1000)
        self._log.info(Fore.BLACK + '[{:04d}] poll end; elapsed processing time: {:d}ms'.format(count, _elapsed_ms))
#       return True

    # ..........................................................................
    def _get_mean_distance(self, orientation, value):
        '''
        Returns the mean of values collected in the queue for the specified IR sensor.
        '''
        if value == None or value == 0:
            return None
        if orientation is Orientation.PORT_SIDE:
            _deque = self._deque_port_side
        elif orientation is Orientation.PORT:
            _deque = self._deque_port
        elif orientation is Orientation.CNTR:
            _deque = self._deque_cntr
        elif orientation is Orientation.STBD:
            _deque = self._deque_stbd
        elif orientation is Orientation.STBD_SIDE:
            _deque = self._deque_stbd_side
        else:
            raise ValueError('unsupported orientation.')
        _deque.append(value)
        _n = 0
        _mean = 0.0
        for x in _deque:
            _n += 1
            _mean += ( x - _mean ) / _n
        if _n < 1:
            return float('nan');
        else:
            return _mean

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
        if value == None or value == 0:
            return None
        self._use_pot = False
#       if self._use_pot:
#           _pot_value = self._pot.get_scaled_value()
#           _EXPONENT = _pot_value
#       else:
#           _pot_value = 0.0
        _EXPONENT = 1.33
        _NUMERATOR = 1000.0
        _distance = pow( _NUMERATOR / value, _EXPONENT ) # 900
#       self._log.debug(Fore.BLACK + Style.NORMAL + 'value: {:>5.2f}; pot value: {:>5.2f}; distance: {:>5.2f}cm'.format(value, _pot_value, _distance))
        return _distance

    # ..........................................................................
    def _callback(self, event, value):
        '''
        This is the callback method from the I²C Master, whose events are
        being returned from the source, e.g., Arduino or IO Expander board.
        '''
        if not self._enabled or self._suppressed:
            self._log.info(Fore.BLACK + Style.DIM + 'SUPPRESSED callback: event {}; value: {:d}'.format(event.name, value))
            return
        try:

#           self._log.debug(Fore.BLACK + 'callback: event {}; value: {:d}'.format(event.name, value))
            _event = None
            _value = value

            # bumpers ..................................................................................

            if event == Event.BUMPER_PORT:
                if value == 1:
                    _event = Event.BUMPER_PORT
                    _value = 1
            elif event == Event.BUMPER_CNTR:
                if value == 1:
                    _event = Event.BUMPER_CNTR
                    _value = 1
            elif event == Event.BUMPER_STBD:
                if value == 1:
                    _event = Event.BUMPER_STBD
                    _value = 1

            # ..........................................................................................
            # For IR sensors we rewrite the value with a dynamic mean distance (cm),
            # setting the event type only if the value is less than a distance threshold.

            elif event == Event.INFRARED_PORT_SIDE:
                _value = self._get_mean_distance(Orientation.PORT_SIDE, self._convert_to_distance(value))
                self._log.info(Fore.RED + Style.BRIGHT + 'mean distance: {:5.2f}cm;\tPORT SIDE'.format(_value))
                if _value != None and _value < self._port_side_trigger_distance:
                    _fire_message(event, _value)
#                   _event = event
#               else:
#                   self._log.info(Fore.RED + 'mean distance: {:5.2f}cm;\tPORT SIDE'.format(_value))

            elif event == Event.INFRARED_PORT:
                _value = self._get_mean_distance(Orientation.PORT, self._convert_to_distance(value))
                self._log.info(Fore.RED + Style.BRIGHT + 'mean distance: {:5.2f}cm;\tPORT'.format(_value))
                if _value != None and _value < self._port_trigger_distance:
                    _fire_message(event, _value)
#                   _event = event
#               else:
#                   self._log.info(Fore.RED + 'mean distance: {:5.2f}cm;\tPORT'.format(_value))

            elif event == Event.INFRARED_CNTR:
                _value = self._get_mean_distance(Orientation.CNTR, self._convert_to_distance(value))
                self._log.info(Fore.BLUE + Style.BRIGHT + 'mean distance: {:5.2f}cm;\tCNTR'.format(_value))
                if _value != None and _value < self._center_trigger_distance:
                    _fire_message(event, _value)
#                   _event = event
#               else:
#                   self._log.info(Fore.BLUE + 'mean distance: {:5.2f}cm;\tCNTR'.format(_value))

            elif event == Event.INFRARED_STBD:
                _value = self._get_mean_distance(Orientation.STBD, self._convert_to_distance(value))
                self._log.info(Fore.GREEN + Style.BRIGHT + 'mean distance: {:5.2f}cm;\tSTBD'.format(_value))
                if _value != None and _value < self._stbd_trigger_distance:
                    _fire_message(event, _value)
#                   _event = event
#               else:
#                   self._log.info(Fore.GREEN + 'mean distance: {:5.2f}cm;\tSTBD'.format(_value))

            elif event == Event.INFRARED_STBD_SIDE:
                _value = self._get_mean_distance(Orientation.STBD_SIDE, self._convert_to_distance(value))
                self._log.info(Fore.GREEN + Style.BRIGHT + 'mean distance: {:5.2f}cm;\tSTBD SIDE'.format(_value))
                if _value != None and _value < self._stbd_side_trigger_distance:
                    _fire_message(event, _value)
#                   _event = event
#               else:
#                   self._log.info(Fore.GREEN + 'mean distance: {:5.2f}cm;\tSTBD SIDE'.format(_value))

#           if _event is not None and _value is not None:
#   #           if not self._ignore_duplicates or ( _event != self._last_event and _value != self._last_value ):
#               _message = self._message_factory.get_message(_event, _value)
#               self._log.info(Fore.WHITE + Style.BRIGHT + 'adding new message eid#{} for event {}'.format(_message.eid, _event.description))
#               self._message_bus.handle(_message)
#   #           else:
#   #               self._log.warning(Fore.CYAN + Style.NORMAL + 'ignoring message for event {}'.format(_event.description))
#               self._last_event = _event
#               self._last_value = _value
#           else:
#               self._log.info(Fore.WHITE + Style.BRIGHT + 'NOT ADDING message eid#{} for event {}'.format(_message.eid, _event.description))

        except Exception as e:
            self._log.error('callback error: {}\n{}'.format(e, traceback.format_exc()))


    # ..........................................................................
    def _fire_message(self, event, value):
        self._log.info(Fore.YELLOW + Style.BRIGHT + 'fire message with event {} and value {}'.format(event, value))
        if event is not None and value is not None:
            _message = self._message_factory.get_message(event, value)
            self._log.info(Fore.WHITE + Style.BRIGHT + 'adding new message eid#{} for event {}'.format(_message.eid, _event.description))
            self._message_bus.handle(_message)
        else:
            self._log.info(Fore.RED + Style.BRIGHT + 'ignoring message with event {} and value {}'.format(event, value))


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
    @property
    def enabled(self):
        return self._enabled

    # ..........................................................................
    def enable(self):
        if not self._enabled:
            if not self._closed:
                self._log.info('enabled.')
                self._enabled = True
            else:
                self._log.warning('cannot enable: already closed.')
        else:
            self._log.warning('already enabled.')

    # ..........................................................................
    def disable(self):
        if self._enabled:
            self._enabled = False
            self._log.info(Fore.YELLOW + 'shutting down thread pool executor...')
            self._executor.shutdown(wait=False) # python 3.9: , cancel_futures=True)
            self._log.info(Fore.YELLOW + 'disabled: thread pool executor has been shut down.')
        else:
            self._log.debug('already disabled.')

    # ..........................................................................
    def close(self):
        '''
        Permanently close and disable the integrated front sensor.
        '''
        if not self._closed:
            self.disable()
            self._closed = True
            self._log.info('closed.')
        else:
            self._log.warning('already closed.')

    # ..........................................................................
    @staticmethod
    def clamp(n, minn, maxn):
        return max(min(maxn, n), minn)

    # ..........................................................................
    @staticmethod
    def remap(x, in_min, in_max, out_min, out_max):
        return (x - in_min) * (out_max - out_min) / (in_max - in_min) + out_min


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
        self._log.info('infrared pin assignments:\t' \
                + Fore.RED + ' port side={:d}; port={:d};'.format(self._port_side_ir_pin, self._port_ir_pin) \
                + Fore.BLUE + ' center={:d};'.format(self._center_ir_pin) \
                + Fore.GREEN + ' stbd={:d}; stbd side={:d}'.format(self._stbd_ir_pin, self._stbd_side_ir_pin))
        # bumpers
        self._port_bmp_pin     = _config.get('port_bmp_pin')      # pin connected to port bumper
        self._center_bmp_pin   = _config.get('center_bmp_pin')    # pin connected to center bumper
        self._stbd_bmp_pin     = _config.get('stbd_bmp_pin')      # pin connected to starboard bumper
        self._log.info('bumper pin assignments:\t' \
                + Fore.RED + ' port={:d};'.format(self._port_ir_pin) \
                + Fore.BLUE + ' center={:d};'.format(self._center_ir_pin ) \
                + Fore.GREEN + ' stbd={:d}'.format(self._stbd_ir_pin))

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

# EOF
