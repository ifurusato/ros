#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# Copyright 2020 by Murray Altheim. All rights reserved. This file is part of
# the Robot Operating System project and is released under the "Apache Licence,
# Version 2.0". Please see the LICENSE file included as part of this package.
#
# author:   Murray Altheim
# created:  2019-12-23
# modified: 2020-03-12
#
# Once running, access the video stream from:    http://pi-address:8001/
#
# source: https://picamera.readthedocs.io/en/release-1.13/recipes2.html#web-streaming
#

import sys, time, traceback
from colorama import init, Fore, Style
init()

from lib.config_loader import ConfigLoader
from lib.logger import Level
from lib.lux import Lux
from lib.video import Video

# main .........................................................................

_video = None
_output = None

def main(argv):

    try:
        # read YAML configuration
        _loader = ConfigLoader(Level.INFO)
        filename = 'config.yaml'
        _config = _loader.configure(filename)
        
        _lux   = Lux(Level.INFO)
        _matrix11x7_stbd_available = True
        _video = Video(_config, _lux, _matrix11x7_stbd_available, Level.INFO)
        _video.start()

        while True:
            time.sleep(1.0)

        _video.stop()

    except KeyboardInterrupt:
        print(Fore.CYAN + Style.BRIGHT + 'caught Ctrl-C; exiting...')
        if _video is not None:
            _video.stop()

    except Exception:
        print(Fore.RED + Style.BRIGHT + 'error starting ros: {}'.format(traceback.format_exc()) + Style.RESET_ALL)


# call main ....................................................................
if __name__== "__main__":
    main(sys.argv[1:])

#EOF
