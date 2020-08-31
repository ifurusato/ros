#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
#  Uses sleep to keep a desired message/sample rate.
#
# derived from:  https://pypi.org/project/nxp-imu
# see MIT license at bottom of file

import time

# ..............................................................................
class Rate(object):
    """
        Uses sleep to keep a desired message/sample rate.
    """
    def __init__(self, hertz):
        self.last_time = time.time()
        self.dt = 1/hertz

    # ..........................................................................
    def sleep(self):
        """
            This uses sleep to delay the function. If your loop is faster than your
            desired Hertz, then this will calculate the time difference so sleep
            keeps you close to you desired hertz. If your loop takes longer than
            your desired hertz, then it doesn't sleep.

            E.g.:

                # grab data at 10Hz
                rate = Rate(10)

                # do something...
                rate.sleep()
        """
        diff = time.time() - self.last_time
        if self.dt > diff:
            time.sleep(self.dt - diff)

        # now that we have slept a while, set the current time as the last time
        self.last_time = time.time()

# ..............................................................................
#
# MIT License
# 
# Copyright (c) 2017 Kevin J. Walchko
# 
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
# 
# The above copyright notice and this permission notice shall be included in all
# copies or substantial portions of the Software.
# 
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.
#
# ..............................................................................
