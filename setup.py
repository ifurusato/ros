#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# author:   Murray Altheim
# created:  2021-02-18
# modified: 2021-02-18
#
# For some reason 'pimoroni-ioexpander' installs but continues
# to show up here as uninstalled. A bug.

import importlib, sys 
import subprocess as sp

from lib.confirm import confirm

libraries = [ \
    'numpy', \
    'pytest', \
    'pyyaml', \
    'colorama', \
    'readchar', \
    'pymessagebus==1.*', \
    'board', \
    'ht0740', \
    'RPi.GPIO', \
    'pigpio', \
    'pimoroni-ioexpander', \
    'adafruit-extended-bus', \
    'adafruit-circuitpython-bno08x', \
    'pyquaternion', \
    'rgbmatrix5x5', \
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
