#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# Copyright 2020-2021 by Murray Altheim. All rights reserved. This file is part
# of the Robot Operating System project, released under the MIT License. Please
# see the LICENSE file included as part of this package.
#
# author:   Murray Altheim
# created:  2020-04-20
# modified: 2020-04-21
#
# Install and run stress test:
#
#   % sudo apt install stress
#   % stress --cpu 4
#

import pytest
import sys, time, traceback, itertools
from subprocess import PIPE, Popen
from colorama import init, Fore, Style
init()

from lib.i2c_scanner import I2CScanner
from lib.config_loader import ConfigLoader
from lib.message_bus import MessageBus
from lib.message_factory import MessageFactory
from lib.clock import Clock
from lib.fan import Fan
from lib.temperature import Temperature
from lib.logger import Level, Logger

# ..............................................................................
@pytest.mark.unit
def test_temperature():
    _temperature = None
    _fan = None
    _log = Logger('temp-test', Level.INFO)
    try:

        # scan I2C bus
        _log.info('scanning I²C address bus...')
        scanner = I2CScanner(_log.level)
        _addresses = scanner.get_int_addresses()

        # load configuration
        _loader = ConfigLoader(Level.INFO)
        filename = 'config.yaml'
        _config = _loader.configure(filename)

        # create Fan if available
        _fan_config = _config['ros'].get('fan')
        _fan_i2c_address = _fan_config.get('i2c_address')
        fan_available = ( _fan_i2c_address in _addresses )
        if fan_available:
            _fan = Fan(_config, Level.INFO)
            _log.info('fan is available at I²C address of 0x{:02X}.'.format( _fan_i2c_address))
        else:
            _fan = None
            _log.info('fan is not available at I²C address of 0x{:02X}.'.format( _fan_i2c_address))

        _message_factory = MessageFactory(Level.INFO)
        _message_bus = MessageBus(Level.DEBUG)
        _clock = Clock(_config, _message_bus, _message_factory, Level.WARN)
        _temperature = Temperature(_config, _clock, _fan, Level.INFO)
        _temperature.enable()
        _counter = itertools.count()
        _clock.enable()
        while True:
            _count = next(_counter)
#           _temperature.display_temperature()
#           _value = _temperature.get_cpu_temperature()
#           _is_warning_temp = _temperature.is_warning_temperature()
#           _is_max_temp = _temperature.is_max_temperature()
#           if _is_warning_temp:
#               _log.warning('[{:04d}] loop; is warning temp? {}; is max temp? {}'.format(_count, _is_warning_temp, _is_max_temp))
#           else:
#               _log.info('[{:04d}] loop; is warning temp? {}; is max temp? {}'.format(_count, _is_warning_temp, _is_max_temp))
            time.sleep(1.0)
    except KeyboardInterrupt:
        _log.info(Fore.YELLOW + 'exited via Ctrl-C' + Style.RESET_ALL)
    except Exception:
        _log.error(Fore.RED + Style.BRIGHT + 'error getting RPI temperature: {}'.format(traceback.format_exc()) + Style.RESET_ALL)
    finally:
        if _temperature:
            _temperature.close()
        if _fan:
            _fan.disable()
#       sys.exit(1)

# main .........................................................................
def main(argv):
    test_temperature()

# call main ....................................................................
if __name__== "__main__":
    main(sys.argv[1:])

#EOF
