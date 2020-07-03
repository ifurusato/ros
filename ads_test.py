#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# Copyright 2020 by Murray Altheim. All rights reserved. This file is part of
# the Robot OS project and is released under the "Apache Licence, Version 2.0".
# Please see the LICENSE file included as part of this package.
#

import sys, signal, time
from colorama import init, Fore, Style
init()

from ads1015 import ADS1015

# exception handler ............................................................
def signal_handler(signal, frame):
    print(Fore.RED + 'Ctrl-C caught: exiting...' + Style.RESET_ALL)
    sys.stderr = DevNull()
    print(Fore.CYAN + 'exit.' + Style.RESET_ALL)
    sys.exit(0)

def main():

    signal.signal(signal.SIGINT, signal_handler)

    print('ads_test          :' + Fore.CYAN + Style.BRIGHT + ' INFO  : starting test...' + Style.RESET_ALL)

    print('ads_test          :' + Fore.YELLOW + Style.BRIGHT + ' INFO  : Press Ctrl+C to exit.' + Style.RESET_ALL)

    CHANNEL_0 = 'in0/ref'
    CHANNEL_1 = 'in1/ref'
    CHANNEL_2 = 'in2/ref'
    ads1015 = ADS1015()
    ads1015.set_mode('single')
    ads1015.set_programmable_gain(2.048)
    ads1015.set_sample_rate(1600)
     
    reference = ads1015.get_reference_voltage()
    print('ads_test          :' + Fore.CYAN + ' INFO  : Reference voltage: {:6.3f}v'.format(reference) + Style.RESET_ALL)
    
    count = 0
    while count < 10:
        count += 1
        value_0 = ads1015.get_compensated_voltage(channel=CHANNEL_0, reference_voltage=reference)
        value_1 = ads1015.get_compensated_voltage(channel=CHANNEL_1, reference_voltage=reference)
        value_2 = ads1015.get_compensated_voltage(channel=CHANNEL_2, reference_voltage=reference)
        print('ads_test          :' + Fore.CYAN + ' INFO  : A0={:6.3f}v; A1={:6.3f}v; A2={:6.3f}v;'.format(value_0, value_1, value_2) + Style.RESET_ALL)
        time.sleep(0.25)

    print('ads_test          :' + Fore.CYAN + Style.BRIGHT + ' INFO  : test complete.' + Style.RESET_ALL)
    


if __name__== "__main__":
    main()

#EOF
