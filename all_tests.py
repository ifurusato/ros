#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# Copyright 2020 by Murray Altheim. All rights reserved. This file is part of
# the Robot OS project and is released under the "Apache Licence, Version 2.0".
# Please see the LICENSE file included as part of this package.
#
# author:  Murray Altheim
# created: 2020-03-16

import time, sys, signal, runpy, subprocess
from colorama import init, Fore, Style
init()

from lib.devnull import DevNull
from lib.logger import Level

# exception handler ............................................................
def signal_handler(signal, frame):
    print(Fore.RED + 'Ctrl-C caught: exiting...' + Style.RESET_ALL)
    sys.stderr = DevNull()
    print(Fore.MAGENTA + 'exit.' + Style.RESET_ALL)
    sys.exit(0)


# ..............................................................................
def main():

    signal.signal(signal.SIGINT, signal_handler)

    try:
        print('all_tests         :' + Fore.CYAN + ' INFO  : executing tests...' + Style.RESET_ALL)


        subprocess.call("ads_test.py", shell=True)

        subprocess.call("batterycheck_test.py", shell=True)

        subprocess.call("rgbmatrix_test.py", shell=True)

        subprocess.call("button_test.py", shell=True)

        subprocess.call("bumpers_test.py", shell=True)

        subprocess.call("infrareds_test.py", shell=True)

        subprocess.call("scanner_test.py", shell=True)

#       subprocess.call("motors_test.py", shell=True)

        time.sleep(5.0)
        print('all_tests         :' + Fore.CYAN + ' INFO  : test complete.' + Style.RESET_ALL)
    
    except KeyboardInterrupt:
        print('all_tests         :' + Fore.RED + Style.BRIGHT + ' INFO  : Ctrl-C caught: complete.' + Style.RESET_ALL)
    except Exception as e:
        print('all_tests         :' + Fore.RED + Style.BRIGHT + ' ERROR : error in test: {}'.format(e) + Style.RESET_ALL)
        traceback.print_exc(file=sys.stdout)
        sys.exit(1)


    finally:
        sys.exit(0)

if __name__== "__main__":
    main()

#EOF
