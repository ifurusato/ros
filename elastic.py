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
#
# see: https://elasticsearch-py.readthedocs.io/en/master/api.html
# server at: http://192.168.1.74:9200/
#

import sys, time, traceback
import json
import requests
import pprint
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
        self._log.info('schema: \'{}\';\tindex: \'{}\';\tdoctype: \'{}\t'.format(self._schema, self._index, self._doc_type))
        self._log.info('connecting to elastic search cluster...')
        self._es = Elasticsearch(host=self._host, port=self._port)
#       self._es = Elasticsearch(
#           ['esnode1', 'esnode2'],
#           # sniff before doing anything
#           sniff_on_start=True,
#           # refresh nodes after a node fails to respond
#           sniff_on_connection_fail=True,
#           # and also every 60 seconds
#           sniffer_timeout=60
#       )
        self._log.info('ready.')

    # ..........................................................................
    def ping(self ):
        if self._es.ping():
            self._log.info('successfully pinged server.')
            return True
        else:
            self._log.warning('unable to ping server.')
            return False

    # ..........................................................................
    def create_index(self):
        _response = self._es.indices.exists(index=self._index)
        if _response:
            self._log.info('index exists?; response: {}'.format(_response))
        else:
            _response = self._es.indices.create(index=self._index, ignore=400)
            self._log.info('created index; response: {}'.format(_response))

    # ..........................................................................
    def delete_index(self):
        _response = self._es.indices.exists(index=self._index)
        if _response:
            self._log.info('index exists?; response: {}'.format(_response))
            _response = self._es.indices.delete(index=self._index)
            self._log.info('index deleted; response: {}'.format(_response))
        else:
            self._log.info('index did not exist.')

    def insert_record(self, oid, data):
        # index and doc_type you can customize by yourself
        _response = self._es.index(index=self._index, doc_type=self._doc_type, id=oid, body=data)
        # index will return insert info: like as created is True or False
        self._log.info(Style.BRIGHT + 'inserted record with oid {}; response:\n'.format(oid) + Fore.GREEN + Style.NORMAL + json.dumps(_response, indent=4))
        return _response

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

    _log = Logger("test", Level.INFO)
    try:

        _level = Level.INFO
        _loader = ConfigLoader(_level)
        filename = 'config.yaml'
        _config = _loader.configure(filename)

        _elastic = Elastic(_config, _level)
        if _elastic.ping():
            _log.info('connected to Elasticsearch service.')
            _elastic.create_index()
    
            _oid = 1
            _response = _elastic.insert_record(_oid, data)
#           parsed = json.loads(_response)
            _log.info('created new record with oid {:d}; response type: {}'.format(_oid, type(_response)))
            _pp = pprint.PrettyPrinter(indent=4)

            _log.info(Fore.YELLOW + 'response: {}'.format(_pp.pprint(_response)))

            _version = _response.get('_version')
            _log.info(Fore.YELLOW + 'version: {}'.format(_version))

            if _version is not None and _version > 10:
                _elastic.delete_index()

            '''
{   '_id': '1',
    '_index': 'kr01',
    '_primary_term': 1,
    '_seq_no': 9,
    '_shards': {'failed': 0, 'successful': 1, 'total': 2},
    '_type': 'pid',
    '_version': 10,
    'result': 'updated'}
            '''


        else:
            _log.info('could not connect to Elasticsearch service; exiting.')
            sys.exit(0)

#       res = es.index(index="test-index", id=1, body=data)
#       print(res['result'])
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
