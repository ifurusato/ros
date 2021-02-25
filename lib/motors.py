#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# Copyright 2020 by Murray Altheim. All rights reserved. This file is part of
# the Robot OS project and is released under the "Apache Licence, Version 2.0".
# Please see the LICENSE file included as part of this package.
#
# author:   Murray Altheim
# created:  2020-01-18
# modified: 2020-08-30
#
# To start pigpiod:
#
#   % sudo systemctl start pigpiod 
#
# To enable/disable pigpiod on boot:
#
#   % sudo systemctl [enable|disable] pigpiod
#
# To control the daemon:
# 
# % sudo systemctl [start|stop|status] pigpiod
#

import sys, time, traceback
from threading import Thread
from fractions import Fraction
from colorama import init, Fore, Style
init()

try:
    import pigpio
except ImportError:
    print(Fore.RED + "This script requires the pigpio module.\nInstall with: sudo apt install python3-pigpio" + Style.RESET_ALL)
#   sys.exit(1)

from lib.logger import Logger, Level
from lib.event import Event
from lib.enums import Direction, Orientation
from lib.slew import SlewRate

# ..............................................................................
class Motors():
    '''
    A dual motor controller with encoders.
    '''
    def __init__(self, config, clock, tb, level):
        super().__init__()
        self._log = Logger('motors', level)
        self._log.info('initialising motors...')
        if config is None:
            raise Exception('no config argument provided.')
        if clock is None:
            raise Exception('no clock argument provided.')
        if tb is None:
            tb = self._configure_thunderborg_motors(level)
            if tb is None:
                raise Exception('unable to configure thunderborg.')
        self._clock = clock
        self._tb = tb
        self._set_max_power_ratio()
        # config pigpio's pi and name its callback thread (ex-API)
        try:
            self._pi = pigpio.pi()
            if self._pi is None:
                raise Exception('unable to instantiate pigpio.pi().')
            elif self._pi._notify is None:
                raise Exception('can\'t connect to pigpio daemon; did you start it?')
            self._pi._notify.name = 'pi.callback'
            self._log.info('pigpio version {}'.format(self._pi.get_pigpio_version()))
            from lib.motor import Motor
            self._log.info('imported Motor.')
        except Exception as e:
            self._log.error('error importing and/or configuring Motor: {}'.format(e))
            traceback.print_exc(file=sys.stdout)
            sys.exit(1)
        self._port_motor = Motor(config, self._clock, self._tb, self._pi, Orientation.PORT, level)
        self._port_motor.set_max_power_ratio(self._max_power_ratio)
        self._stbd_motor = Motor(config, self._clock, self._tb, self._pi, Orientation.STBD, level)
        self._stbd_motor.set_max_power_ratio(self._max_power_ratio)
        self._closed  = False
        self._enabled = False # used to be enabled by default
        # a dictionary of motor # to last set value
        self._msgIndex = 0
        self._last_set_power = { 0:0, 1:0 }
        self._log.info('motors ready.')

    # ..........................................................................
    def name(self):
        return 'Motors'

    # ..........................................................................
    def _configure_thunderborg_motors(self, level):
        '''
        Import the ThunderBorg library, then configure the Motors.
        '''
        self._log.info('configure thunderborg & motors...')
        global pi
        try:
            self._log.info('importing thunderborg...')
            import lib.ThunderBorg3 as ThunderBorg
            self._log.info('successfully imported thunderborg.')
            TB = ThunderBorg.ThunderBorg(level)  # create a new ThunderBorg object
            TB.Init()                       # set the board up (checks the board is connected)
            self._log.info('successfully instantiated thunderborg.')

            if not TB.foundChip:
                boards = ThunderBorg.ScanForThunderBorg()
                if len(boards) == 0:
                    self._log.error('no thunderborg found, check you are attached.')
                else:
                    self._log.error('no ThunderBorg at address {:02x}, but we did find boards:'.format(TB.i2cAddress))
                    for board in boards:
                        self._log.info('board {:02x} {:d}'.format(board, board))
                    self._log.error('if you need to change the I²C address change the setup line so it is correct, e.g. TB.i2cAddress = {:0x}'.format(boards[0]))
                sys.exit(1)
            TB.SetLedShowBattery(True)
            return TB

        except Exception as e:
            self._log.error('unable to import thunderborg: {}'.format(e))
            traceback.print_exc(file=sys.stdout)
            sys.exit(1)

    # ..........................................................................
    def set_led_show_battery(self, enable):
        self._tb.SetLedShowBattery(enable)

    # ..........................................................................
    def set_led_color(self, color):
        self._tb.SetLed1(color.red/255.0, color.green/255.0, color.blue/255.0)

    # ..........................................................................
    def _set_max_power_ratio(self):
        pass
        # initialise ThunderBorg ...........................
        self._log.info('getting battery reading...')
        # get battery voltage to determine max motor power
        # could be: Makita 12V or 18V power tool battery, or 12-20V line supply
        voltage_in = self._tb.GetBatteryReading()
        if voltage_in is None:
            raise OSError('cannot continue: cannot read battery voltage.')
        self._log.info('voltage in:  {:>5.2f}V'.format(voltage_in))
#       voltage_in = 20.5
        # maximum motor voltage
        voltage_out = 9.0
        self._log.info('voltage out: {:>5.2f}V'.format(voltage_out))
        if voltage_in < voltage_out:
            raise OSError('cannot continue: battery voltage too low ({:>5.2f}V).'.format(voltage_in))
        # Setup the power limits
        if voltage_out > voltage_in:
            self._max_power_ratio = 1.0
        else:
            self._max_power_ratio = voltage_out / float(voltage_in)
        # convert float to ratio format
        self._log.info('battery level: {:>5.2f}V; motor voltage: {:>5.2f}V;'.format( voltage_in, voltage_out) + Fore.CYAN + Style.BRIGHT \
                + ' maximum power ratio: {}'.format(str(Fraction(self._max_power_ratio).limit_denominator(max_denominator=20)).replace('/',':')))

    # ..........................................................................
    def get_motor(self, orientation):
        if orientation is Orientation.PORT:
            return self._port_motor
        else:
            return self._stbd_motor

    # ..........................................................................
    def is_in_motion(self):
        '''
        Returns true if either motor is moving.
        '''
        return self._port_motor.is_in_motion() or self._stbd_motor.is_in_motion()

    # ..........................................................................
    def get_steps(self):
        '''
        Returns the port and starboard motor step count.
        '''
        return [ self._port_motor.get_steps() , self._stbd_motor.get_steps() ]

    # ..........................................................................
    def get_current_power_level(self, orientation):
        '''
        Returns the last set power of the specified motor.
        '''
        if orientation is Orientation.PORT:
            return self._port_motor.get_current_power_level()
        else:
            return self._stbd_motor.get_current_power_level()

    # ..........................................................................
    def interrupt(self):
        '''
        Interrupt any motor loops by setting the _interrupt flag.
        '''
        self._port_motor.interrupt()
        self._stbd_motor.interrupt()

    # ..........................................................................
    def halt(self):
        '''
        Quickly (but not immediately) stops both motors.
        '''
        self._log.info('halting...')
        if self.is_stopped():
            _tp = Thread(name='halt-port', target=self.processStop, args=(Event.HALT, Orientation.PORT))
            _ts = Thread(name='hapt-stbd', target=self.processStop, args=(Event.HALT, Orientation.STBD))
            _tp.start()
            _ts.start()
        else:
            self._log.debug('already stopped.')
        self._log.info('halted.')
        return True

    # ..........................................................................
    def brake(self):
        '''
        Slowly coasts both motors to a stop.
        '''
        self._log.info('braking...')
        if self.is_stopped():
            _tp = Thread(name='brake-port', target=self.processStop, args=(Event.BRAKE, Orientation.PORT))
            _ts = Thread(name='brake-stbd', target=self.processStop, args=(Event.BRAKE, Orientation.STBD))
            _tp.start()
            _ts.start()
        else:
            self._log.warning('already stopped.')
        self._log.info('braked.')
        return True

    # ..........................................................................
    def stop(self):
        '''
        Stops both motors immediately, with no slewing.
        '''
        self._log.info('stopping...')
        if not self.is_stopped():
            self._port_motor.stop()
            self._stbd_motor.stop()
            self._log.info('stopped.')
        else:
            self._log.warning('already stopped.')
        return True

    # ..........................................................................
    def is_stopped(self):
        return self._port_motor.is_stopped() and self._stbd_motor.is_stopped()

    # ..........................................................................
    def processStop(self, event, orientation):
        '''
        Synchronised process control over various kinds of stopping.
        '''
        if orientation is Orientation.PORT:
            if event is Event.HALT:
                self._log.info('halting port motor...')
                self._port_motor.halt()
            elif event is Event.BRAKE:
                self._log.info('braking port motor...')
                self._port_motor.brake()
            else: # is stop
                self._log.info('stopping port motor...')
                self._port_motor.stop()
        else:
            if event is Event.HALT:
                self._log.info('halting starboard motor...')
                self._stbd_motor.halt()
            elif event is Event.BRAKE:
                self._log.info('braking starboard motor...')
                self._stbd_motor.brake()
            else: # is stop
                self._log.info('stopping starboard motor...')
                self._stbd_motor.stop()
        self.print_current_power_levels()

    # ..........................................................................
    def get_current_power_levels(self):
        '''
        Returns the last set power values.
        '''
        _port_power = self._port_motor.get_current_power_level()
        _stbd_power = self._stbd_motor.get_current_power_level()
        return [ _port_power, _stbd_power ]

    # ..........................................................................
    def print_current_power_levels(self):
        '''
        Prints the last set power values.
        '''
        self._msgIndex += 1
        self._log.info('{}:\tcurrent power:\t{:6.1f}\t{:6.1f}'.format(self._msgIndex, self._last_set_power[0], self._last_set_power[1]))

    # ..........................................................................
    def enable(self):
        '''
        Enables the motors, clock and velocity calculator. This issues
        a warning if already enabled, but no harm is done in calling
        it repeatedly.
        '''
        if self._enabled:
            self._log.warning('already enabled.')
        if not self._port_motor.enabled:
            self._port_motor.enable()
        if not self._stbd_motor.enabled:
            self._stbd_motor.enable()
        self._clock.enable()
        self._enabled = True
        self._log.info('enabled.')

    # ..........................................................................
    def disable(self):
        '''
        Disable the motors, halting first if in motion.
        '''
        if self._enabled:
            self._log.info('disabling...')
            self._enabled = False
            if self.is_in_motion(): # if we're moving then halt
                self._log.warning('event: motors are in motion (halting).')
                self.halt()
            self._port_motor.disable()
            self._stbd_motor.disable()
            self._log.info('disabling pigpio...')
            self._pi.stop()
            self._log.info('disabled.')
        else:
            self._log.debug('already disabled.')

    # ..........................................................................
    def close(self):
        '''
        Halts, turn everything off and stop doing anything.
        '''
        if not self._closed:
            if self._enabled:
                self.disable()
            self._log.info('closing...')
            self._port_motor.close()
            self._stbd_motor.close()
            self._closed = True
            self._log.info('closed.')
        else:
            self._log.debug('already closed.')

    # ..........................................................................
    @staticmethod
    def cancel():
        print('cancelling motors...')
        Motor.cancel()

#EOF
