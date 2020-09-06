#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#### - - coding: latin-1 -*-

# import dependency libraries ..................................................

import sys, traceback
from fractions import Fraction

from lib.enums import Orientation
from lib.logger import Logger, Level

# ..............................................................................
class MotorConfigurer():
    '''
        Configures the Thunderborg motor controller. 
    '''
    def __init__(self, ros,  config, level):
        self._log = Logger("mtrconf", level)
        if config is None:
            raise ValueError('null configuration argument.')
        self._config = config

    # ..........................................................................
    def configure(self):
        '''
            Import the ThunderBorg library, then configure and return the Motors.
        '''
        self._log.info('configure thunderborg & motors...')
        try:
            self._log.info('importing ThunderBorg...')
            import lib.ThunderBorg3 as ThunderBorg
            self._log.info('successfully imported ThunderBorg.')
            TB = ThunderBorg.ThunderBorg(Level.INFO)  # create a new ThunderBorg object
            TB.Init()                       # set the board up (checks the board is connected)
            self._log.info('successfully instantiated ThunderBorg.')

            if not TB.foundChip:
                boards = ThunderBorg.ScanForThunderBorg()
                if len(boards) == 0:
                    self._log.error('No ThunderBorg found, check you are attached :)')
                else:
                    self._log.error('No ThunderBorg at address %02X, but we did find boards:' % (TB.i2cAddress))
                    for board in boards:
                        self._log.info('    %02X (%d)' % (board, board))
                    self._log.error('If you need to change the I²C address change the setup line so it is correct, e.g. TB.i2cAddress = 0x{}'.format(boards[0]))
                sys.exit(1)
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

        except Exception as e:
            self._log.error('unable to import ThunderBorg: {}'.format(e))
            traceback.print_exc(file=sys.stdout)
            sys.exit(1)

        # now import motors
        from lib.motors import Motors
        try:
            self._log.info('getting raspberry pi...')
            self._log.info('configuring motors...')
            self._motors = Motors(self._config, TB, Level.INFO)
            self._motors.get_motor(Orientation.PORT).set_max_power_ratio(_max_power_ratio)
            self._motors.get_motor(Orientation.STBD).set_max_power_ratio(_max_power_ratio)
            return self._motors
        except OSError as oe:
            self._log.error('failed to configure motors: {}'.format(oe))
#           sys.stderr = DevNull()
            sys.exit(1)

            
#EOF
