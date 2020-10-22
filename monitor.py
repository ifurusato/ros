#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# Copyright 2020 by Murray Altheim. All rights reserved. This file is part of
# the Robot OS project and is released under the "Apache Licence, Version 2.0".
# Please see the LICENSE file included as part of this package.
#
# author:   Murray Altheim
# created:  2020-08-25
# modified: 2020-08-25
#
#  This starts top or htop (the system monitor) on a TFT display connected to
#  the Raspberry Pi, assuming it's connected as /dev/tty0. This uses a Python
#  subprocess so that the command executes and then returns.
#
#  This is kinda a work in progress, trying various approaches to see which
#  might be usable in a daemon capacity.
#

import os, psutil, sys
from threading import Thread
from subprocess import run, Popen, PIPE

_app = 'top'
_is_running = _app in (p.name() for p in psutil.process_iter())

if not _is_running:
    os.system("sudo sh -c 'htop > /dev/tty0'")
#   proc = Popen(['sudo', 'sh', '-c', 'htop', '>/dev/tty0'], stdout=PIPE, stderr=PIPE)
#   proc = run(['sudo', 'sh', '-c', 'htop', '>/dev/tty0'], stdout=PIPE, stderr=PIPE)
#   proc.communicate()
#   t = Thread(target = lambda: os.system("sudo sh -c 'htop > /dev/tty0' &"))
#   t.start()
    sys.exit(0)
else:
    print('top already running.')
    sys.exit(0)

# EOF
