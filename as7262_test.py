#!/usr/bin/env python3

import time
import os
import sys
from as7262 import AS7262

as7262 = AS7262()

BAR_CHAR = u'\u2588'

ANSI_COLOR_RED = '\x1b[31m'
ANSI_COLOR_GREEN = '\x1b[32m'
ANSI_COLOR_YELLOW = '\x1b[33m'
ANSI_COLOR_BLUE = '\x1b[34m'
ANSI_COLOR_MAGENTA = '\x1b[35m'

MAX_VALUE = 14000.0
BAR_WIDTH = 25

as7262.set_gain(64)
as7262.set_integration_time(17.857)
as7262.set_measurement_mode(2)
as7262.set_illumination_led(1)

try:
    input = raw_input
except NameError:
    pass

input("Setting white point baseline.\n\nHold a white sheet of paper ~5cm in front of the sensor and press a key...\n")
baseline = as7262.get_calibrated_values()
time.sleep(1)
input("Baseline set. Press a key to continue...\n")
sys.stdout.flush()

try:
    while True:
        values = as7262.get_calibrated_values()
        values = [int(x/y*MAX_VALUE) for x,y in zip(list(values), list(baseline))]
        values = [int(min(value, MAX_VALUE) / MAX_VALUE * BAR_WIDTH) for value in values]
        red, orange, yellow, green, blue, violet = [(BAR_CHAR * value) + (' ' * (BAR_WIDTH - value)) for value in values]

        sys.stdout.write('\x1b[0;1H')
        sys.stdout.write(u"""       Spectrometer Bar Graph        
 ---------------------------------     
|Red:    {}{}\x1b[0m|     
|Orange: {}{}\x1b[0m|     
|Yellow: {}{}\x1b[0m|     
|Green:  {}{}\x1b[0m|     
|Blue:   {}{}\x1b[0m|     
|Violet: {}{}\x1b[0m|     
 ---------------------------------     
                                 
""".format(
    ANSI_COLOR_RED, red,
    ANSI_COLOR_YELLOW, orange,
    ANSI_COLOR_YELLOW, yellow,
    ANSI_COLOR_GREEN, green,
    ANSI_COLOR_BLUE, blue,
    ANSI_COLOR_MAGENTA, violet
))
        sys.stdout.flush()
        time.sleep(0.5)

except KeyboardInterrupt:
    as7262.set_measurement_mode(3)
    as7262.set_illumination_led(0)


