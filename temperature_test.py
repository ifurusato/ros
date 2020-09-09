#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# Copyright 2020 by Murray Altheim. All rights reserved. This file is part of
# the Robot OS project and is released under the "Apache Licence, Version 2.0".
# Please see the LICENSE file included as part of this package.
#
# author:   Murray Altheim
# created:  2020-04-20
# modified: 2020-04-21
#

import sys, time, traceback
from subprocess import PIPE, Popen
from colorama import init, Fore, Style
init()

from lib.config_loader import ConfigLoader
from lib.queue import MessageQueue
from lib.temperature import Temperature
from lib.logger import Level, Logger

# main .........................................................................
def main(argv):

    _temp = None
    _log = Logger('temp-test', Level.INFO)

    try:

        # read YAML configuration
        _loader = ConfigLoader(Level.INFO)
        filename = 'config.yaml'
        _config = _loader.configure(filename)
        _queue = MessageQueue(Level.DEBUG)

        _temp = Temperature(_config, _queue, Level.INFO)
        _temp.enable()

        while True:
#           _value = _temp.get_cpu_temperature()
#           _is_hot = _temp.is_hot()
            time.sleep(1.0)

    except KeyboardInterrupt:
        _log.info(Fore.YELLOW + 'exited via Ctrl-C' + Style.RESET_ALL)
        if _temp:
            _temp.close()
        sys.exit(0)

    except Exception:
        _log.error(Fore.RED + Style.BRIGHT + 'error getting RPI temperature: {}'.format(traceback.format_exc()) + Style.RESET_ALL)
        if _temp:
            _temp.close()
        sys.exit(1)


# call main ....................................................................
if __name__== "__main__":
    main(sys.argv[1:])

#EOF
