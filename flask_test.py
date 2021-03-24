#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# Copyright 2020 by Murray Altheim. All rights reserved. This file is part of
# the Robot Operating System project and is released under the "Apache Licence, 
# Version 2.0". Please see the LICENSE file included as part of this package.
#
# author:   Murray Altheim
# created:  2019-12-23
# modified: 2021-03-24
#

import sys, time, traceback
from flask_wrapper import FlaskWrapperService

from lib.logger import Logger, Level

# main .........................................................................
def main(argv):

    _flask_wrapper = None

    try:
        print('starting web service...')
        _flask_wrapper = FlaskWrapperService()
        _flask_wrapper.start()
        print('web service started.')
        while True:
            time.sleep(1.0)

    except KeyboardInterrupt:
        print('caught Ctrl-C interrupt.')
    except Exception:
        print('error starting ros: {}'.format(traceback.format_exc()))
    finally:
        if _flask_wrapper:
            _flask_wrapper.close()

# call main ....................................................................
if __name__== "__main__":
    main(sys.argv[1:])

#EOF
