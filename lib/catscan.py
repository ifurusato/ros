#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# Copyright 2020 by Murray Altheim. All rights reserved. This file is part of
# the Robot OS project and is released under the "Apache Licence, Version 2.0".
# Please see the LICENSE file included as part of this package.
#
# author:   altheim
# created:  2020-03-31
# modified: 2020-03-31

# Import library functions we need
import time, threading
from colorama import init, Fore, Style
init()

try:
    import numpy
except ImportError:
    exit("This script requires the numpy module\nInstall with: sudo pip3 install numpy")

try:
    from gpiozero import MotionSensor
    print('import            :' + Fore.BLACK + ' INFO  : successfully imported gpiozero MotionSensor.' + Style.RESET_ALL)
except Exception:
    print('import            :' + Fore.RED + ' ERROR : unable to import gpiozero MotionSensor, exiting...' + Style.RESET_ALL)
    sys.exit(1)

from lib.servo import Servo
from lib.logger import Logger, Level
from lib.event import Event
from lib.message import Message
from lib.rgbmatrix import RgbMatrix, DisplayType

_mutex = threading.Lock()

# ..............................................................................
class CatScan():
    '''
        Uses an infrared PIR sensor to scan for cats. This involves raising a
        servo arm holding the sensor.
    '''
    def __init__(self, config, queue, level):
        self._log = Logger('cat-scan', Level.INFO)
        self._config = config
        self._queue = queue
        if self._config:
            self._log.info('configuration provided.')
            _config = self._config['ros'].get('cat_scan')
            self._active_angle = _config.get('active_angle')
            self._inactive_angle = _config.get('inactive_angle')
            _pir_pin = _config.get('pir_pin')
            _servo_number = _config.get('servo_number')  
        else:
            self._log.warning('no configuration provided.')
            self._active_angle = -90.0
            self._inactive_angle = 90.0
            _pir_pin = 15
            _servo_number = 3

        _threshold_value = 0.1 # the value above which the device will be considered “on”
        self._log.info('cat scan active angle: {:>5.2f}°; inactive angle: {:>5.2f}°'.format(self._active_angle, self._inactive_angle))
        self._servo = Servo(self._config, _servo_number, level)
#       set up pin where PIR is connected
        self._sensor = MotionSensor(_pir_pin, threshold=_threshold_value, pull_up=False)
        self._sensor.when_motion    = self._activated
        self._sensor.when_no_motion = None #self._deactivated
        self._scan_enabled = False
        self._disabling = False
        self._enabled = False
        self._closed = False
        # arm behaviour
        self._arm_movement_degree_step = 5.0
        self._arm_up_delay             = 0.09
        self._arm_down_delay           = 0.04
        self._rgbmatrix = RgbMatrix(Level.INFO)
        self._rgbmatrix.set_display_type(DisplayType.SCAN)
        self._log.info('ready.')


    # ..........................................................................
    def _warning_display(self):
        self._rgbmatrix.disable()
        self._rgbmatrix.set_display_type(DisplayType.RANDOM)
        self._rgbmatrix.enable()


    # ..........................................................................
    def _activated(self):
        '''
            The default function called when the sensor is activated.
        '''
        if self._enabled and self._scan_enabled:
            self._log.info('cat sensed.')
            self._log.info(Fore.RED + Style.BRIGHT + 'detected CAT!')
            self._queue.add(Message(Event.CAT_SCAN))
            self.set_mode(False)
            self._warning_display()
        else:
            self._log.info('[DISABLED] activated catscan.')


    # ..........................................................................
    def _deactivated(self):
        '''
            The default function called when the sensor is deactivated.
        '''
        if self._enabled:
            self._log.info('deactivated catscan.')
        else:
            self._log.debug('[DISABLED] deactivated catscan.')


    # ..........................................................................
    def is_waiting(self):
        '''
            Returns true if the scan is in progress.
        '''
        return self._scan_enabled


    # ..........................................................................
    def set_mode(self, active):
        '''
            Sets the mode to active or inactive. This raises or lowers the servo arm.
        '''
        if not self._enabled:
            self._log.warning('cannot scan: disabled.')
            return

        _current_angle = self._servo.get_position(-999.0)
        self._log.critical('current angle: {:>4.1f}°'.format(_current_angle))
        if active:
            if _current_angle != -999.0 and _current_angle is not self._active_angle:
                with _mutex:
                    for degrees in numpy.arange(self._inactive_angle, self._active_angle + 0.01, -1.0 * self._arm_movement_degree_step):
                        self._log.debug('position set to: {:>4.1f}°'.format(degrees))
                        self._servo.set_position(degrees)
                        time.sleep(self._arm_up_delay)
                self._log.info('position set to active.')
            else:
                self._log.warning('position already set to active.')
            # wait until it settles

            self._log.info('waiting for motion detector to settle...')
            time.sleep(1.0)
            while self._sensor.motion_detected:
                self._log.debug('still waiting...')
                time.sleep(0.1)
#           time.sleep(5.0)
            self._scan_enabled = True
            self._rgbmatrix.enable()
        else:
            self._scan_enabled = False
            self._rgbmatrix.disable()
            if _current_angle != -999.0 and _current_angle is not self._inactive_angle:
                with _mutex:
                    for degrees in numpy.arange(self._active_angle, self._inactive_angle + 0.1, self._arm_movement_degree_step):
                        self._log.debug('position set to: {:>4.1f}°'.format(degrees))
                        self._servo.set_position(degrees)
                        time.sleep(self._arm_down_delay)
                self._log.info('position set to inactive.')
            else:
                self._log.warning('position already set to inactive.')
    

    # ..........................................................................
    def enable(self):
        self._log.debug('enabling...')
        if self._closed:
            self._log.warning('cannot enable: closed.')
            return
#       self._tof.enable()
        self._enabled = True
        self._log.debug('enabled.')


    # ..........................................................................
    def disable(self):
        if self._disabling:
            self._log.warning('already disabling.')
        else:
            self._disabling = True
            self._enabled = False
            self._rgbmatrix.disable()
            self._log.debug('disabling...')
            self.set_mode(False)
            self._servo.disable()
            self._servo.close()
            self._disabling = False
            self._log.debug('disabled.')


    # ..........................................................................
    def close(self):
        self.disable()
        self._closed = True


#EOF
