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
# This test blinks an LED connected to pin 5 of the Arduino. This requires 
# a Raspberry Pi connected to an Arduino over I²C on address 0x08. Because
# an LED cannot directly handle a 5 volt supply you should connect the LED
# to ground through a resistor of about 330 ohms. The exact value will
# depend on the dropping voltage of the LED (which varies) and how bright
# you want it to appear.
#
# This also requires installation of pigpio, e.g.:
#
#   % sudo pip3 install pigpio
#

from lib.logger import Level
#from lib.i2c_master_pigpio import I2cMaster
from lib.i2c_master import I2cMaster

# ..............................................................................
def main():

    try:
        _pin = 7
        _device_id = 0x08  # must match Arduino's SLAVE_I2C_ADDRESS
        _master = I2cMaster(_device_id, Level.INFO)
        if _master is not None: 
     
            _master.test_blink_led(_pin, 50) # see documentation for hardware configuration
         
            _master.close()

        else:
            raise Exception('unable to establish contact with Arduino on address 0x{:02X}'.format(_device_id))

    except KeyboardInterrupt:
        self._log.warning('Ctrl-C caught; exiting...')


if __name__== "__main__":
    main()

#EOF
