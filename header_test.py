#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# created:  2020-10-05
# modified: 2020-10-05
#
# see: https://stackoverflow.com/questions/3391076/repeat-string-to-certain-length
#

import math, sys, time, traceback
from colorama import init, Fore, Style
init()

RULER='''
         1         2         3         4         5         6         7         8         9         C         1         2
123456789012345678901234567890123456789012345678901234567890123456789012345678901234567890123456789012345678901234567890
'''

'''
[INFO] --------------------------< net.ohau:tekapo >---------------------------
[INFO] Building tekapo 0.0.2-SNAPSHOT                                   [10/10]
[INFO] --------------------------------[ jar ]---------------------------------
'''


from lib.logger import Logger, Level


# ..............................................................................
def main():

    try:
        _log = Logger('test', Level.INFO)

        print(Fore.BLACK + Style.BRIGHT + RULER + Style.RESET_ALL)

        _base = 'abcdefghijklmnopqrtsuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789012345678901234567890'
        _max_width = 80
        _margin    = 27  # right-most colon is column 27
        _available_width = _max_width - _margin

#       for i in range(1, _available_width):
        for i in range(1, _available_width + 2):
            _title = _base[:i]
            _message1 = _base[:i]
            _message2 = '[{:d}/{:d}]'.format(i, 10)
            _log.header(_title, _message1, _message2)

        _log.header(' ', None, None)
        _log.header('com.google.code.gson:gson', None, None)
        _log.header('commons-io:fileutils', 'Here\'s a message we want to display.', None)
        _log.header('org.apache.commons:commons-lang3', 'Here\'s another message we want to display.', '[3/10]')

        print(Fore.BLACK + Style.BRIGHT + RULER + Style.RESET_ALL)

    except Exception as e:
        _log.error('error in splenk processor: {}'.format(e))
        traceback.print_exc(file=sys.stdout)


if __name__== "__main__":
    main()

#EOF
