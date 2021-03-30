#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# Copyright 2020-2021 by Murray Altheim. All rights reserved. This file is part
# of the Robot Operating System project, released under the MIT License. Please
# see the LICENSE file included as part of this package.
#
# author:   Murray Altheim
# created:  2021-02-18
# modified: 2021-02-18
#
# For some reason 'pimoroni-ioexpander' installs but continues to show up here
# as uninstalled. A bug?
#
# You may also need to install various libraries via apt.
#
# sudo apt install i2c-tools
# sudo apt install evtest tslib libts-bin					
# sudo apt install pigpio
#

import importlib, sys
import subprocess as sp

from lib.confirm import confirm

libraries = [ \
    'numpy', \
    'pytest', \
    'pyyaml', \
    'colorama', \
    'rpi.gpio', \
    'gpiozero', \
    'board', \
    'adafruit-extended-bus', \
    'readchar', \
    'pymessagebus==1.*', \
    'ht0740', \
    'pimoroni-ioexpander', \
    'adafruit-circuitpython-bno08x', \
    'pyquaternion', \
    'matrix11x7', \
    'rgbmatrix5x5', \
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
        _command = 'pip3 install --user {}'.format(name, name)
        print('This script requires the {} module.\nInstall with: {}'.format(name, _command))
        confirmed = confirm(True)
        if confirmed:
            _comleted_process = sp.run(_command, shell=True)
            print('-- return code {}'.format(_comleted_process.returncode))
            if _comleted_process.returncode == 0:
                print('-- installation successful.')
            else:
                print('-- returned error code \'{}\' on command \'{}\''.format(_comleted_process.returncode, _command))
                sys.exit(_comleted_process.returncode)
        else:
            print('-- exiting loop.')
            sys.exit(0)

print('-- complete.')

#EOF
