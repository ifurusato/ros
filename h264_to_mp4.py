#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# Copyright 2020 by Murray Altheim. All rights reserved. This file is part of
# the Robot Operating System project and is released under the "Apache Licence, 
# Version 2.0". Please see the LICENSE file included as part of this package.
#
# author:   Murray Altheim
# created:  2020-08-19
# modified: 2020-08-19
# 
# A simple script that converts an h264 to mp4 video file using ffmpeg, which
# must already be installed.
#

import os, sys
from colorama import init, Fore, Style
init()

if len(sys.argv) != 2:
    print(Fore.RED + 'ERROR: expected 1 command line argument: path to h264 source file.' + Style.RESET_ALL)
    sys.exit(1)
   
#print('number of arguments: {:d} arguments.'.format(len(sys.argv)))
#print('argument List: {}'.format(str(sys.argv)))

h264_filename = sys.argv[1]
if not os.path.isfile(h264_filename):
    print(Fore.RED + 'ERROR: source file {} does not exist.'.format(h264_filename) + Style.RESET_ALL)
    sys.exit(1)
print(Fore.CYAN + Style.DIM + '-- source file: {}'.format(h264_filename) + Style.RESET_ALL)

basename, ext = os.path.splitext(h264_filename)
mp4_filename  = basename + '.mp4'

if os.path.isfile(mp4_filename):
    print(Fore.RED + 'ERROR: target file {} already exists.'.format(mp4_filename) + Style.RESET_ALL)
    sys.exit(1)
print(Fore.CYAN + Style.DIM + '-- target file: {}'.format(mp4_filename) + Style.RESET_ALL)

print(Fore.GREEN + Style.BRIGHT + '-- converting {}...'.format(h264_filename) + Style.RESET_ALL)
#ffmpeg -loglevel panic -hide_banner -r 24 -i $h264_filename -vcodec copy $mp4_filename 
os.system('ffmpeg -loglevel info -hide_banner -r 24 -i ' + h264_filename + ' -vcodec copy ' + mp4_filename )

print(Fore.CYAN + '-- complete: wrote to target file: {}'.format(mp4_filename) + Style.RESET_ALL)

#EOF
