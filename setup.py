#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# author:   Murray Altheim
# created:  2021-02-18
# modified: 2021-02-18
#

import sys, importlib


libraries = [ 'numpy', \
    'pytest', \
    'colorama', \
    'readchar', \
    'pymessagebus==1.*', \
    'pimoroni-ioexpander', \
    'RPi.GPIO', \
    'pigpio', \
    'gpiozero', \
    ]

for name in libraries:
    try:
        print('-- processing {}...'.format(name))
        _index = name.find('=')
        if _index == -1:
            print('   importing: {}'.format(name))
            importlib.import_module(name, package=None)
        else:
            name = name[:_index].strip()
            print('   importing: {}'.format(name))
            importlib.import_module(name, package=None)
    except RuntimeError as e:
        print('error on import of {}: {}'.format(name, e))
    except ImportError:
        print('')
        sys.exit("This script requires the {} module.\nInstall with: sudo pip3 install {}".format(name, name))

print('complete.')

#EOF
