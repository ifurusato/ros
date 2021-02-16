#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# Copyright 2020 by Murray Altheim. All rights reserved. This file is part of
# the Robot Operating System project and is released under the "Apache Licence, 
# Version 2.0". Please see the LICENSE file included as part of this package.
#
# author:   Murray Altheim
# created:  2020-10-05
# modified: 2021-02-07
#

import sys, traceback
from fractions import Fraction

from lib.enums import Orientation
from lib.logger import Logger, Level

# ..............................................................................
class MockMotorConfigurer():
    '''
    Configures a mock ThunderBorg motor controller for a pair of mock motors. 

    :param config:       the application configuration
    :param clock:        the 'system' clock providing timing for velocity calculation
    :param enable_mock:  if set True a failure to instantiate the ThunderBorg will instead use a mock
    :param level:        the logging level
    '''
    def __init__(self, config, clock, enable_mock=False, level=Level.INFO):
        self._log = Logger("motor-conf", level)
        if config is None:
            raise ValueError('null configuration argument.')
        if clock is None:
            raise ValueError('null clock argument.')
        self._config = config
        # Import the ThunderBorg library, then configure and return the Motors.
        self._log.info('configure thunderborg & motors...')
        try:

            import lib.MockThunderBorg3 as ThunderBorg
            self._log.info('successfully imported MockThunderBorg.')

            TB = ThunderBorg.ThunderBorg(Level.INFO)  # create a new ThunderBorg object
            TB.Init()                       # set the board up (checks the board is connected)
            self._log.info('successfully instantiated mock ThunderBorg.')
            TB.SetLedShowBattery(True)
    
            # initialise ThunderBorg ...........................
            self._log.debug('getting battery reading...')
            # get battery voltage to determine max motor power
            # could be: Makita 12V or 18V power tool battery, or 12V line supply
            voltage_in = TB.GetBatteryReading()
            if voltage_in is None:
                raise OSError('cannot continue: cannot read battery voltage.')
            self._log.info('voltage in: {:>5.2f}V'.format(voltage_in))
    #       voltage_in = 20.5
            # maximum motor voltage
            voltage_out = 9.0
            self._log.info('voltage out: {:>5.2f}V'.format(voltage_out))
            if voltage_in < voltage_out:
                raise OSError('cannot continue: battery voltage too low ({:>5.2f}V).'.format(voltage_in))
            # Setup the power limits
            if voltage_out > voltage_in:
                _max_power_ratio = 1.0
            else:
                _max_power_ratio = voltage_out / float(voltage_in)
            # convert float to ratio format
            self._log.info('battery level: {:>5.2f}V; motor voltage: {:>5.2f}V; maximum power ratio: {}'.format(voltage_in, voltage_out, \
                    str(Fraction(_max_power_ratio).limit_denominator(max_denominator=20)).replace('/',':')))

        except OSError as e:
            if enable_mock:
                self._log.info('using mock ThunderBorg.')
                import lib.MockThunderBorg3 as ThunderBorg
            else:
                self._log.error('unable to import ThunderBorg: {}'.format(e))
                traceback.print_exc(file=sys.stdout)
                raise Exception('unable to instantiate ThunderBorg [2].')
        except Exception as e:
            if enable_mock:
                self._log.info('using mock ThunderBorg.')
                import lib.MockThunderBorg3 as ThunderBorg
            else:
                self._log.error('unable to import ThunderBorg: {}'.format(e))
                traceback.print_exc(file=sys.stdout)
                raise Exception('unable to instantiate ThunderBorg [2].')
#               sys.exit(1)

        # now import motors
        from mock.motors import MockMotors
        try:
            self._log.info('getting raspberry pi...')
            self._log.info('configuring motors...')
            self._motors = MockMotors(self._config, clock, TB, Level.INFO)
            self._motors.get_motor(Orientation.PORT).set_max_power_ratio(_max_power_ratio)
            self._motors.get_motor(Orientation.STBD).set_max_power_ratio(_max_power_ratio)
        except OSError as oe:
            self._log.error('failed to configure motors: {}'.format(oe))
            self._motors = None
#           sys.stderr = DevNull()
            raise Exception('unable to instantiate ThunderBorg [3].')
#           sys.exit(1)
        self._log.info('ready.')

    # ..........................................................................
    def get_motors(self):
        '''
        Return the configured motors.
        '''
        return self._motors
            
#EOF
