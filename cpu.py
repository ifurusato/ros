#!/usr/bin/env python3

import sys, time
from colorama import init, Fore, Style
init()

try:
    import psutil
except ImportError:
    sys.exit("This script requires the psutil module\nInstall with: sudo pip install psutil")

from matrix11x7 import Matrix11x7

print(Fore.GREEN + Style.NORMAL + """
    Matrix 11x7: CPU

    Displays a graph with CPU values.

""" + Fore.RED + Style.NORMAL + """
    Press Ctrl+C to exit.

""" + Style.RESET_ALL)

try:

    matrix11x7 = Matrix11x7()
    matrix11x7.set_brightness(0.5)  # avoid retina-searage!
    # uncomment if the display is upside down
    # matrix11x7.rotate(degrees=180)

    cpu_values = [0] * matrix11x7.width

    while True:

        cpu_values.pop(0)
        cpu_values.append(psutil.cpu_percent())
        matrix11x7.set_graph(cpu_values, low=0, high=25)
        matrix11x7.show()
        time.sleep(0.2)

except KeyboardInterrupt:
    pass
finally:
    matrix11x7.clear()

