#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# Copyright 2020 by Murray Altheim. All rights reserved. This file is part of
# the Robot Operating System project and is released under the "Apache Licence,
# Version 2.0". Please see the LICENSE file included as part of this package.
#
# author:   Murray Altheim
# created:  2020-10-11
# modified: 2020-10-11
#
# This converts a delimited string to a single JSON-ND record
#
# see:  https://github.com/glenkleidon/JSON-ND
# 22:31:53.279.798985    |pid|kp     |ki     |kd     |p.cp   |p.ci   |p.cd   |p.lpw|p.cpw|p.spwr|p.cvel|p.stpt|s.cp|s.ci   |s.cd   |s.lpw  |s.cpw|s.spw|s.cvel|s.stpt|p.stps|s.stps|
# 22:31:53.332.682610    |pid| 0.0950| 0.0000| 0.0003| 0.0000| 0.0000| 0.0000| 0.00| 0.00|  0.00| 0.00 | -0.00|0   | 0.0000| 0.0000| 0.0000| 0.00| 0.00|  0.00| 0.00 | -0.00|0     |
# 22:31:53.382.751703    |pid| 0.0950| 0.0000| 0.0003|-0.0000| 0.0000|-0.0000| 0.00| 0.00|  0.00| 0.00 | -0.00|0   |-0.0000| 0.0000|-0.0000| 0.00| 0.00|  0.00| 0.00 | -0.00|0     |
# 22:31:53.468.258858    |pid| 0.0950| 0.0000| 0.0003|-0.0000| 0.0000|-0.0000| 0.00| 0.00|  0.00| 0.00 | -0.00|0   |-0.0000| 0.0000|-0.0000| 0.00| 0.00|  0.00| 0.00 | -0.00|0     |

import sys, traceback
import csv, json
from collections import OrderedDict
from colorama import init, Fore, Style
init()

from lib.logger import Logger, Level

class JsonNdParserException(Exception):
    pass

class JsonNdParser(object):

    def __init__(self, delim, level, include_datatype=True):
        self._log = Logger("jnp", level)
        self._delim = delim
        self._log.info('delimiter: \'{}\''.format(delim))
        self._include_datatype = include_datatype
        self._log.info('include datatype: {}'.format(self._include_datatype))
        csv.register_dialect( "csv-vbar", delimiter = self._delim)
        self._log.info('ready.')

    #...........................................................................
    def parse_file(self, filename):
        '''
           Parse the CSV file to a List of JSON strings.
        '''
        _list = []
        try:
            with open(filename) as csv_file:
                _header = []
                csv_reader = csv.reader(csv_file, delimiter='|')
                _line_count = 0
                for _row_data in csv_reader:
                    if _line_count == 0: # then reada header
                        self._log.debug('raw column names are: {}'.format(', '.join(_row_data) ))
                        for i in range(len(_row_data)-1):
                            if i == 0:
                                _header.append('@timestamp')
                            elif i == 1:
                                _header.append('row')
                            else:
                                _value = _row_data[i].strip()
                                _header.append(_value)
                        self._log.info('header field names:\n' + Fore.YELLOW + '{}'.format(', '.join(_header) ))
                        _line_count += 1
                    else:
                        _json_row = self._parse_row(_header, _row_data, _line_count)
                        _list.append(_json_row)
                        _line_count += 1
            self._log.info('processed {} lines.'.format(_line_count))
        except Exception as e:
            raise JsonNdParserException('error parsing CSV to JSON: {}\n{}'.format(e, traceback.format_exc()))

        self._log.info('returning list of {} elements.'.format(len(_list)))
        return _list

    #...........................................................................
    def _parse_row(self, header, row, line_count):
        '''
           Parse the row, returning it as a JSON string. 
           This uses the header to provide field names.
        '''
        _row_dict = OrderedDict()
        self._log.debug('processing row {}...'.format(line_count))
        for i in range(len(row)-1):
            _value = row[i].strip()
            if i == 0:
                _datatype = 'date'
            elif i == 1:
                _datatype = 'integer'
                _value = line_count
            elif '.' in _value:
                _datatype = 'float'
                _value = float(_value)
            else:
                _datatype = 'integer'
                _value = int(_value)
            if self._include_datatype:
                self._log.debug(Fore.MAGENTA + '[{}] datatype: {}; value: \'{}\''.format( i, _datatype, _value))
                _row_dict[ '{}:{}'.format(header[i],_datatype)] = _value
            else:
                _row_dict[ '{}'.format(header[i])] = _value

        _json_row = json.dumps(_row_dict)
        self._log.debug(Fore.BLUE + 'JSON:\n{}'.format(_json_row) + Style.RESET_ALL)
        self._log.info('processed row {}.'.format(line_count))
        return _json_row


## main .........................................................................
#def main(argv):
#
#    _log = Logger("test", Level.INFO)
#
#    try:
#
#        _jnp = JsonNdParser('|', Level.INFO)
#        _log.info('parsing data...')
#        _filename = 'pid_log_3.csv'
#
#        _log.info('parsing file: {}...'.format(_filename))
#        # returns a List of strings
#        _response = _jnp.parse_file(_filename)
#        _log.info('got response with {} records.'.format(len(_response)) )
#
#        for i in range(len(_response)):
#            _row = _response[i]
#            _log.info('row [{}]:\n'.format(i) + Fore.YELLOW + _row)
#
#        _log.info('done.')
#
#    except Exception:
#        _log.error('error parsing to JSON-ND: {}'.format(traceback.format_exc()))
#
## call main ....................................................................
#if __name__== "__main__":
#    main(sys.argv[1:])

#EOF
