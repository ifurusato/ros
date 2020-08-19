#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# Copyright 2020 by Murray Altheim. All rights reserved. This file is part of
# the Robot OS project and is released under the "Apache Licence, Version 2.0".
# Please see the LICENSE file included as part of this package.
#
# author:  Murray Altheim
# created: 2020-03-16
#
# A test script that plays various MP3 sound files.
#

import time, sys, signal, runpy, subprocess
from colorama import init, Fore, Style
init()

from lib.devnull import DevNull
from lib.logger import Level, Logger
from lib.player import Sound, Player

# exception handler ............................................................
def signal_handler(signal, frame):
    print(Fore.RED + 'Ctrl-C caught: exiting...' + Style.RESET_ALL)
    sys.stderr = DevNull()
    print(Fore.MAGENTA + 'exit.' + Style.RESET_ALL)
    sys.exit(0)

# ..............................................................................
def main():

    signal.signal(signal.SIGINT, signal_handler)

    _log = Logger('play_test', Level.INFO)

    try:
        _log.info('executing player tests...')

        _player = Player(Level.INFO)

        _player.play(Sound.BLIP)
        time.sleep(3.0)

        _player.play(Sound.ALARM)
        time.sleep(3.0)

        _log.info('test complete.')
    
    except KeyboardInterrupt:
        _log.warning('Ctrl-C caught: complete.')
    except Exception as e:
        _log.error('error in test: {}'.format(e))
        traceback.print_exc(file=sys.stdout)
        sys.exit(1)
    finally:
        sys.exit(0)

if __name__== "__main__":
    main()

#EOF
