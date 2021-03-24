#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# Copyright 2020-2021 by Murray Altheim. All rights reserved. This file is part
# of the Robot Operating System project, released under the MIT License. Please
# see the LICENSE file included as part of this package.
#
# author:  altheim
# created: 2020-02-14
#
#  Scans the I²C bus, returning a list of devices.
#
# see: https://www.raspberrypi.org/forums/viewtopic.php?t=114401
# see: https://raspberrypi.stackexchange.com/questions/62612/is-there-anyway-to-scan-i2c-using-pure-python-libraries:q
#
# If you're getting a "Permission denied" message due to smbus, add the pi user to the i2c group using: 
#
#  % sudo adduser pi i2c
#
# then reboot.
#

import errno
from lib.logger import Level, Logger

from colorama import init, Fore, Style
init()

class I2CScanner():
    '''
    Scans the I²C bus, returning a list of devices.
    '''
    def __init__(self, level):
        super().__init__()
        self._log = Logger('i2cscan', level)
        self._log.debug('initialising...')
        self._int_list = []
        self._hex_list = []
        try:
            import smbus
            bus_number = 1  # 1 indicates /dev/i2c-1
            self._bus = smbus.SMBus(bus_number)
            self._log.info('ready.')
        except ImportError:
            self._log.warning('initialised. This script requires smbus. Will operate without but return an empty result.')
            self._bus = None

    # ..........................................................................
    def get_hex_addresses(self):
        '''
        Returns a hexadecimal version of the list.
        '''
        self._scan_addresses()
        return self._hex_list

    # ..........................................................................
    def get_int_addresses(self):
        '''
        Returns an integer version of the list.
        '''
        self._scan_addresses()
        return self._int_list

    # ..........................................................................
    def has_address(self, addresses):
        '''
        Performs the address scan (if necessary) and returns true if a device
        is available at any of the specified addresses.
        '''
        self._scan_addresses()
        for address in addresses:
            if address in self._int_list:
                return True
        return False

    # ..........................................................................
    def _scan_addresses(self):
        '''
        Scans the bus and returns the available device addresses. After being
        called and populating the int and hex lists, this closes the connection
        to smbus.
        '''
        if len(self._int_list) == 0:
            device_count = 0
            if self._bus is not None:
                for address in range(3, 128):
                    try:
                        self._bus.write_byte(address, 0)
                        self._log.debug('found I²C device at 0x{:02X}'.format(address))
                        self._int_list.append(address)
                        self._hex_list.append(hex(address))
                        device_count = device_count + 1
                    except IOError as e:
                        if e.errno != errno.EREMOTEIO:
                            self._log.error('Error: {0} on address {1}'.format(e, hex(address)))
                    except Exception as e: # exception if read_byte fails
                        self._log.error('Error unk: {0} on address {1}'.format(e, hex(address)))
                self._bus.close()
                self._bus = None
                self._log.info("found {:d} device(s).".format(device_count))
            else:
                self._log.info("found no devices (no smbus available).")
        return self._int_list

    # end class ................................................................

# main .........................................................................

THUNDERBORG_ADDRESS = 0x15

def main():

    level = Level.INFO
    log = Logger('main', level)
    log.info('scanning for I2C devices...')
    scanner = I2CScanner(Level.INFO)

    _addresses = scanner.get_int_addresses()
    log.info('available I2C device(s):')
    if len(_addresses) == 0:
        log.warning('no devices found.')
        return
    else:
        for n in range(len(_addresses)):
            address = _addresses[n]
            log.info('device: {0} ({1})'.format(address, hex(address)))

    for i in range(len(_addresses)):
        print(Fore.CYAN + '-- address: {}'.format(_addresses[i]) + Style.RESET_ALL)

    print('')

    if THUNDERBORG_ADDRESS in _addresses:
        print(Fore.CYAN + '-- thunderborg found at address {}: using motors/motor'.format(THUNDERBORG_ADDRESS) + Style.RESET_ALL)
#       from motors import Motors
#       from motor import Motor
    else:
        print(Fore.MAGENTA + '-- thunderborg not found at address {}: using motors/motor'.format(THUNDERBORG_ADDRESS) + Style.RESET_ALL)
#       from z_motors import Motors
#       from z_motor import Motor


if __name__== "__main__":
    main()

#EOF

