#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# Copyright 2020 by Murray Altheim. All rights reserved. This file is part of
# the Robot Operating System project and is released under the "Apache Licence, 
# Version 2.0". Please see the LICENSE file included as part of this package.
#
# author:   Murray Altheim
# created:  2020-08-23
# modified: 2020-08-31
#
# derived from:  https://pypi.org/project/nxp-imu

import time

# ..............................................................................
class Rate():

    def __init__(self, hertz):
        self._last_time = time.time()
        self._dt = 1/hertz

    # ..........................................................................
    def wait(self):
        """
            If called before the allotted period will wait the remaining time
            so that the loop is no faster than the specified frequency. If
            called after the allotted period has passed, no waiting takes place.

            E.g.:

                # execute loop at 60Hz
                rate = Rate(60)

                while True:
                    # do something...
                    rate.wait()

        """
        _diff = time.time() - self._last_time
        if self._dt > _diff:
            time.sleep(self._dt - _diff)
        self._last_time = time.time()

#EOF
