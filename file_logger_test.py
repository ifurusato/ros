#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# Copyright 2020 by Murray Altheim. All rights reserved. This file is part of
# the Robot OS project and is released under the "Apache Licence, Version 2.0".
# Please see the LICENSE file included as part of this package.
#

from lib.logger import Logger, Level

# call main ......................................


def main():

    _log = Logger("logger", Level.INFO, log_to_file=True)

    for i in range(10):
        _log.file("log message {}".format(i))   
        print("log message {}".format(i))   

if __name__ == "__main__":
    main()

