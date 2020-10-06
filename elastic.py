#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# Copyright 2020 by Murray Altheim. All rights reserved. This file is part of
# the Robot OS project and is released under the "Apache Licence, Version 2.0".
# Please see the LICENSE file included as part of this package.
#
# author:   altheim
# created:  2020-10-02
# modified: 2020-10-02

import sys, time, traceback
import requests
from elasticsearch import Elasticsearch
from colorama import init, Fore, Style
init()

from lib.config_loader import ConfigLoader
from lib.logger import Logger, Level

# ..............................................................................
class Elastic():
    '''
        Access to an elasticsearch service.
    '''

    # ..........................................................................
    def __init__(self, config, level):
        self._log = Logger("elastic", level)
        if config is None:
            raise ValueError('no configuration provided.')
        _config = config['ros'].get('elastic')
        self._host     = _config.get('host')
        self._port     = _config.get('port')
        self._log.info('service address: {}:{}'.format(self._host, self._port))
        self._schema   = _config.get('schema')
        self._index    = _config.get('index')
        self._doc_type = _config.get('doc_type')
        self._log.info('schema: \'{}\'; index: \t{}\t; doctype: \'{}\t'.format(self._schema, self._index, self._doc_type))
        self._log.info('connecting to elastic search cluster...')
        self._es = Elasticsearch(host=self._host, port=self._port)
        self._log.info('ready.')

    # ..........................................................................
    def ping(self ):
        if self._es.ping():
            self._log.info('successfully pinged server.')
        else:
            self._log.warning('unable to ping server.')

    # ..........................................................................
    def create_index(self, index):
        self._es.indices.create(index=index, ignore=400)

    def insert_one_data(self, _index, data):
        # index and doc_type you can customize by yourself
        _response = self._es.index(index=self._index, doc_type=self._doc_type, id=5, body=data)
        # index will return insert info: like as created is True or False
        self._log.info('inserted; response: {}'.format(_response))

    # ..........................................................................
    def get(self):
        _response = requests.get(self._host)
        self._log.info('response: {}'.format(_response.content))
        pass

    # ..........................................................................
    def put(self, message):
        '''
            Sends the message to the Elasticsearch service.
        '''
        self._log.info('message: {}'.format(message))
        pass

data = {
        "author": "Chestermo",
        "gender": "male",
        "age": "24",
        "body_fat": "15%",
        "interest": ["couch potato", "eat and sleep"]
    }

# main .........................................................................
def main(argv):

    try:

        _level = Level.INFO
        _loader = ConfigLoader(_level)
        filename = 'config.yaml'
        _config = _loader.configure(filename)

        _elastic = Elastic(_config, _level)
        _elastic.ping()
#       _elastic.get()

#       _name = 'test-kr01'
#       _elastic.create_index(_name)
#       _elastic.insert_one_data(_name, data)

    except Exception:
        print(Fore.RED + Style.BRIGHT + 'error starting ros: {}'.format(traceback.format_exc()) + Style.RESET_ALL)

# call main ....................................................................
if __name__== "__main__":
    main(sys.argv[1:])

#EOF
