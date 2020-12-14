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
import itertools, time, threading
import datetime as dt
from collections import deque as Deque
from colorama import init, Fore, Style
init()

from lib.config_loader import ConfigLoader
from lib.logger import Logger, Level
from lib.enums import Orientation
from lib.event import Event
from lib.message_factory import MessageFactory
from lib.message_bus import MessageBus
from lib.message import Message
from lib.rate import Rate
#from lib.indicator import Indicator
from lib.pot import Potentiometer # for calibration only
from lib.ioe import IoExpander

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
    def __init__(self, config, clock, message_bus, message_factory, level):
        if config is None:
            raise ValueError('no configuration provided.')
        self._log = Logger("ifs", level)
        self._log.info('configuring integrated front sensor...')
        self._clock = clock
        self._message_bus = message_bus
        if message_factory:
            self._message_factory = message_factory
        else:
            self._message_factory = MessageFactory(level)
        self._config = config['ros'].get('integrated_front_sensor')
        self._ignore_duplicates            = self._config.get('ignore_duplicates')
        self._loop_freq_hz                 = self._config.get('loop_freq_hz')
        _use_pot                           = self._config.get('use_potentiometer')
        self._pot = Potentiometer(config, Level.INFO) if _use_pot else None
        if self._loop_freq_hz:
            self._rate = Rate(self._loop_freq_hz)
            self._tick_modulo = None
        else:
            self._tick_modulo              = self._config.get('tick_modulo')
            self._log.info('tick modulo: {:d}'.format(self._tick_modulo) )
            self._clock.add_consumer(self)
        # event thresholds:
        self._cntr_raw_min_trigger         = self._config.get('cntr_raw_min_trigger')
        self._oblq_raw_min_trigger         = self._config.get('oblq_raw_min_trigger')
        self._side_raw_min_trigger         = self._config.get('side_raw_min_trigger')
        self._cntr_trigger_distance_cm     = self._config.get('cntr_trigger_distance_cm')
        self._oblq_trigger_distance_cm     = self._config.get('oblq_trigger_distance_cm')
        self._side_trigger_distance_cm     = self._config.get('side_trigger_distance_cm')
        self._log.info('event thresholds:    \t' \
                +Fore.RED + ' port side={:>5.2f}; port={:>5.2f};'.format(self._side_trigger_distance_cm, self._oblq_trigger_distance_cm) \
                +Fore.BLUE + ' center={:>5.2f};'.format(self._cntr_trigger_distance_cm) \
                +Fore.GREEN + ' stbd={:>5.2f}; stbd side={:>5.2f}'.format(self._oblq_trigger_distance_cm, self._side_trigger_distance_cm))
        # hardware pin assignments
        self._port_bmp_pin                 = self._config.get('port_bmp_pin')
        self._center_bmp_pin               = self._config.get('center_bmp_pin')
        self._stbd_bmp_pin                 = self._config.get('stbd_bmp_pin')
        self._log.info('bumper pin assignments:\t' \
                +Fore.RED + ' port={:d};'.format(self._port_bmp_pin) \
                +Fore.BLUE + ' center={:d};'.format(self._center_bmp_pin) \
                +Fore.GREEN + ' stbd={:d}'.format(self._stbd_bmp_pin))
        self._port_side_ir_pin             = self._config.get('port_side_ir_pin')
        self._port_ir_pin                  = self._config.get('port_ir_pin')
        self._center_ir_pin                = self._config.get('center_ir_pin')
        self._stbd_ir_pin                  = self._config.get('stbd_ir_pin')
        self._stbd_side_ir_pin             = self._config.get('stbd_side_ir_pin')
        self._log.info('infrared pin assignments:\t' \
                +Fore.RED + ' port side={:d}; port={:d};'.format(self._port_side_ir_pin, self._port_ir_pin) \
                +Fore.BLUE + ' center={:d};'.format(self._center_ir_pin) \
                +Fore.GREEN + ' stbd={:d}; stbd side={:d}'.format(self._stbd_ir_pin, self._stbd_side_ir_pin))
        _max_workers                       = self._config.get('max_workers')
#       self._executor = ProcessPoolExecutor(max_workers=_max_workers)
        self._log.info('creating thread pool executor with maximum of {:d} workers.'.format(_max_workers))
        self._executor = ThreadPoolExecutor(max_workers=_max_workers, thread_name_prefix='ifs')
        # create/configure IO Expander
        self._ioe = IoExpander(config, Level.INFO)
        self._clock.add_consumer(self._ioe)
        # these are used to support running averages
        _queue_limit = 2 # larger number means it takes longer to change
        self._deque_cntr      = Deque([], maxlen=_queue_limit)
        self._deque_port      = Deque([], maxlen=_queue_limit)
        self._deque_stbd      = Deque([], maxlen=_queue_limit)
        self._deque_port_side = Deque([], maxlen=_queue_limit)
        self._deque_stbd_side = Deque([], maxlen=_queue_limit)
        # ...
        self._thread     = None
        self._last_event = None
        self._last_value = None
        self._enabled    = False
        self._suppressed = False
        self._closed     = False
        self._count      = 0
        self._counter    = itertools.count()
        self._group      = 0
        self._log.info('ready.')

    # ..........................................................................
    def get_IOExpander(self):
        '''
        Return a reference to the internal IO Expander board.
        This is used for testing.
        '''
        return self._ioe

    # ..........................................................................
    def _loop(self):
        while self._enabled:
            _count = next(self._counter)
            _future = self._executor.submit(self._poll, _count, lambda: self.enabled )
            self._rate.wait()

    # ..........................................................................
    def add(self, message):
        '''
        Reacts to every nth (modulo) TICK message, submitting a _poll Thread
        from the thread pool executor, which polls the various sensors and
        sending callbacks for each.

        Note that if the loop frequency is set this method is disabled.
        '''
#       if not self._enabled or self._suppressed:
        if self._enabled and message.event is Event.CLOCK_TICK:
            if ( message.value % self._tick_modulo ) == 0:
                _future = self._executor.submit(self._poll, message.value, lambda: self.enabled )

    # ..........................................................................
    def _poll(self, count, f_is_enabled):
        '''
        Poll the various infrared and bumper sensors, executing callbacks for each.
        In tests this typically takes 173ms from ItsyBitsy, 85ms from the Pimoroni IO Expander.

        This uses 'poll groups' so that all sensors are read upon each poll.

          Group 0: the bumpers
          Group 1: the center infrared sensor
          Group 2: the oblique infrared sensors
          Group 3: the side infrared sensors

        Note that the bumpers are handled entirely differently, using a "charge pump" debouncer,
        running off a modulo of the clock TICKs.
        '''
        if not f_is_enabled():
            self._log.warning('[{:04d}] poll not enabled'.format(count))
            return

        _group = self._get_sensor_group()
        _current_thread = threading.current_thread()
        _current_thread.name = 'poll-{:d}'.format(_group)
        _start_time = dt.datetime.now()

        if _group == 0: # bumper group .........................................
            self._log.debug(Fore.WHITE + '[{:04d}] BUMP ifs poll start; group: {}'.format(count, _group))

            # port bumper sensor ...........................
            _port_bmp_data     = self._ioe.get_port_bmp_value()
            if _port_bmp_data == 1:
                _message = self._message_factory.get_message(Event.BUMPER_PORT, _port_bmp_data)
                self._log.debug(Fore.RED + 'adding new message eid#{} for BUMPER_PORT event.'.format(_message.eid))
                self._message_bus.handle(_message)

            # center bumper sensor .........................
            _cntr_bmp_data     = self._ioe.get_center_bmp_value()
            if _cntr_bmp_data == 1:
                _message = self._message_factory.get_message(Event.BUMPER_CNTR, _cntr_bmp_data)
                self._log.debug(Fore.BLUE + 'adding new message eid#{} for BUMPER_CNTR event.'.format(_message.eid))
                self._message_bus.handle(_message)

            # stbd bumper sensor ...........................
            _stbd_bmp_data     = self._ioe.get_stbd_bmp_value()
            if _stbd_bmp_data == 1:
                _message = self._message_factory.get_message(Event.BUMPER_STBD, _stbd_bmp_data)
                self._log.debug(Fore.GREEN + 'adding new message eid#{} for BUMPER_STBD event.'.format(_message.eid))
                self._message_bus.handle(_message)

        elif _group == 1: # center infrared group ..............................
            self._log.debug(Fore.BLUE + '[{:04d}] CNTR ifs poll start; group: {}'.format(count, _group))
            _cntr_ir_data      = self._ioe.get_center_ir_value()
            if _cntr_ir_data > self._cntr_raw_min_trigger:
                self._log.debug(Fore.BLUE + '[{:04d}] ANALOG IR ({:d}):       \t'.format(count, 3) + (Fore.RED if (_cntr_ir_data > 100.0) else Fore.YELLOW) \
                        + Style.BRIGHT + '{:d}'.format(_cntr_ir_data) + Style.DIM + '\t(analog value 0-255)')
                _value = self._get_mean_distance(Orientation.CNTR, self._convert_to_distance(_cntr_ir_data))
                if _value != None and _value < self._cntr_trigger_distance_cm:
                    self._log.debug(Fore.BLUE + Style.DIM + 'CNTR     \tmean distance:\t{:5.2f}/{:5.2f}cm'.format(_value, self._cntr_trigger_distance_cm) + Style.DIM + '; raw: {:d}'.format(_cntr_ir_data))
                    _message = self._message_factory.get_message(Event.INFRARED_CNTR, _value)
                    self._message_bus.handle(_message)

        elif _group == 2: # oblique infrared group .............................
            self._log.debug(Fore.YELLOW + '[{:04d}] OBLQ ifs poll start; group: {}'.format(count, _group))

            # port analog infrared sensor ..................
            _port_ir_data      = self._ioe.get_port_ir_value()
            if _port_ir_data > self._oblq_raw_min_trigger:
                self._log.debug('[{:04d}] ANALOG IR ({:d}):       \t'.format(count, 2) + (Fore.RED if (_port_ir_data > 100.0) else Fore.YELLOW) \
                        + Style.BRIGHT + '{:d}'.format(_port_ir_data) + Style.DIM + '\t(analog value 0-255)')
                _value = self._get_mean_distance(Orientation.PORT, self._convert_to_distance(_port_ir_data))
                if _value != None and _value < self._oblq_trigger_distance_cm:
                    self._log.debug(Fore.RED + Style.DIM + 'PORT     \tmean distance:\t{:5.2f}/{:5.2f}cm'.format(_value, self._oblq_trigger_distance_cm) + Style.DIM + '; raw: {:d}'.format(_port_ir_data))
                    _message = self._message_factory.get_message(Event.INFRARED_PORT, _value)
                    self._message_bus.handle(_message)

            # starboard analog infrared sensor .............
            _stbd_ir_data      = self._ioe.get_stbd_ir_value()
            if _stbd_ir_data > self._oblq_raw_min_trigger:
                self._log.debug('[{:04d}] ANALOG IR ({:d}):       \t'.format(count, 4) + (Fore.RED if (_stbd_ir_data > 100.0) else Fore.YELLOW) \
                        + Style.BRIGHT + '{:d}'.format(_stbd_ir_data) + Style.DIM + '\t(analog value 0-255)')
                _value = self._get_mean_distance(Orientation.STBD, self._convert_to_distance(_stbd_ir_data))
                if _value != None and _value < self._oblq_trigger_distance_cm:
                    self._log.debug(Fore.GREEN + Style.DIM + 'STBD     \tmean distance:\t{:5.2f}/{:5.2f}cm'.format(_value, self._oblq_trigger_distance_cm) + Style.DIM + '; raw: {:d}'.format(_stbd_ir_data))
                    _message = self._message_factory.get_message(Event.INFRARED_STBD, _value)
                    self._message_bus.handle(_message)

        elif _group == 3: # side infrared group ................................
            self._log.debug(Fore.RED + '[{:04d}] SIDE ifs poll start; group: {}'.format(count, _group))

            # port side analog infrared sensor .............
            _port_side_ir_data = self._ioe.get_port_side_ir_value()
            if _port_side_ir_data > self._side_raw_min_trigger:
                self._log.debug(Fore.RED + '[{:04d}] ANALOG IR ({:d}):       \t'.format(count, 1) + (Fore.RED if (_port_side_ir_data > 100.0) else Fore.YELLOW) \
                        + Style.BRIGHT + '{:d}'.format(_port_side_ir_data) + Style.DIM + '\t(analog value 0-255)')
                _value = self._get_mean_distance(Orientation.PORT_SIDE, self._convert_to_distance(_port_side_ir_data))
                if _value != None and _value < self._side_trigger_distance_cm:
                    self._log.debug(Fore.RED + Style.DIM + 'PORT_SIDE\tmean distance:\t{:5.2f}/{:5.2f}cm'.format(_value, self._side_trigger_distance_cm) + Style.DIM + '; raw: {:d}'.format(_port_side_ir_data))
                    _message = self._message_factory.get_message(Event.INFRARED_PORT_SIDE, _value)
                    self._message_bus.handle(_message)

            # starboard side analog infrared sensor ........
            _stbd_side_ir_data = self._ioe.get_stbd_side_ir_value()
            if _stbd_side_ir_data > self._side_raw_min_trigger:
                self._log.debug('[{:04d}] ANALOG IR ({:d}):       \t'.format(count, 5) + (Fore.RED if (_stbd_side_ir_data > 100.0) else Fore.YELLOW) \
                        + Style.BRIGHT + '{:d}'.format(_stbd_side_ir_data) + Style.DIM + '\t(analog value 0-255)')
                _value = self._get_mean_distance(Orientation.STBD_SIDE, self._convert_to_distance(_stbd_side_ir_data))
                if _value != None and _value < self._side_trigger_distance_cm:
                    self._log.debug(Fore.GREEN + Style.DIM + 'STBD_SIDE\tmean distance:\t{:5.2f}/{:5.2f}cm'.format(_value, self._side_trigger_distance_cm) + Style.DIM + '; raw: {:d}'.format(_stbd_side_ir_data))
                    _message = self._message_factory.get_message(Event.INFRARED_STBD_SIDE, _value)
                    self._message_bus.handle(_message)
        else:
            raise Exception('invalid group number: {:d}'.format(_group))

        _delta = dt.datetime.now() - _start_time
        _elapsed_ms = int(_delta.total_seconds() * 1000)
        self._log.debug(Fore.BLACK + '[{:04d}] poll end; elapsed processing time: {:d}ms'.format(count, _elapsed_ms))

    # ......................................................
    def _get_sensor_group(self):
        '''
        Loops 0-3 to select the sensor group.
        '''
        if self._group == 3:
            self._group = 0
        else:
            self._group += 1
#       self._log.debug(Fore.BLACK + 'group: {:d}'.format(self._group))
        return self._group

    # ..........................................................................
    def _get_mean_distance(self, orientation, value):
        '''
        Returns the mean of values collected in the queue for the specified IR sensor.
        '''
        if value == None or value == 0:
            return None
        if orientation is Orientation.CNTR:
            _deque = self._deque_cntr
        elif orientation is Orientation.PORT:
            _deque = self._deque_port
        elif orientation is Orientation.STBD:
            _deque = self._deque_stbd
        elif orientation is Orientation.PORT_SIDE:
            _deque = self._deque_port_side
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
        if self._pot:
            _EXPONENT = self._pot.get_scaled_value()
        else:
            _EXPONENT = 1.27 #1.33
        _NUMERATOR = 1000.0
        _distance = pow( _NUMERATOR / value, _EXPONENT ) # 900
        if self._pot:
            self._log.info(Fore.YELLOW + 'value: {:>5.2f}; pot value: {:>5.2f}; distance: {:>5.2f}cm'.format(value, _EXPONENT, _distance))
        return _distance

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
                if self._thread is None:
                    self._thread = threading.Thread(name='ifs-poll', target=self._loop, args=())
                    self._thread.start()
                else:
                    self._log.error('poll thread already running.')
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
            self._log.debug('already closed.')

    # ..........................................................................
    @staticmethod
    def clamp(n, minn, maxn):
        return max(min(maxn, n), minn)

    # ..........................................................................
    @staticmethod
    def remap(x, in_min, in_max, out_min, out_max):
        return (x - in_min) * (out_max - out_min) / (in_max - in_min) + out_min

# EOF
