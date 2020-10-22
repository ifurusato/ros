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
# See:
#  local server at: http://192.168.1.74:9200/
#  https://github.com/glenkleidon/JSON-ND
# Elasticsearch Python:
#   https://elasticsearch-py.readthedocs.io/en/master/api.html
# Elasticsearch:
#   https://www.elastic.co/guide/en/elasticsearch/reference/current/rest-apis.html
#   https://www.elastic.co/guide/en/elasticsearch/reference/current/indices.html
#   https://www.elastic.co/guide/en/elasticsearch/reference/current/docs.html
#   https://www.elastic.co/guide/en/elasticsearch/reference/current/search.html
#   https://www.elastic.co/guide/en/elasticsearch/reference/current/graph-explore-api.html
# Grafana:
#   https://grafana.com/docs/grafana/latest/datasources/elasticsearch/
#   https://www.metricfire.com/blog/using-grafana-with-elasticsearch-tutorial/
#   https://qbox.io/blog/how-to-use-grafana-to-pull-data-from-elasticsearch
#   https://fabianlee.org/2017/01/15/grafana-connecting-to-an-elasticsearch-datasource/
#
# get all documents in index:
#   http://192.168.1.74:9200/kr01/_search?q=*:*

import sys, time, traceback
import json
import requests
import pprint
try:
    from elasticsearch import Elasticsearch
except ImportError as ie:
    _lib = 'elasticsearch'
    sys.exit("This script requires the {lib} module.\n"\
           +"Install with: sudo pip3 install {lib}".format(lib=_lib))

from colorama import init, Fore, Style
init()

from lib.config_loader import ConfigLoader
from lib.jsonnd import JsonNdParser, JsonNdParserException
from lib.logger import Logger, Level


# ..............................................................................
class Elastic(object):
    '''
        Configurable access to an elasticsearch service with support for 
        basic search engine API calls.
    '''

    # ..........................................................................
    def __init__(self, config, level):
        self._log = Logger("elastic", level)
        if config is None:
            raise ValueError('no configuration provided.')
        _config = config['ros'].get('elastic')
        self._host = _config.get('host')
        self._port = _config.get('port')
        self._log.info('service address: {}:{}'.format(self._host, self._port))
        self._schema = _config.get('schema')
        self._index = _config.get('index')
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
    def ping(self):
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
            # ignore 400 cause by IndexAlreadyExistsException when creating an index
            _response = self._es.indices.create(index=self._index, ignore=400)
            self._log.info('created index; response: {}'.format(_response))

    # ..........................................................................
    def get_index(self):
        _response = self._es.indices.get(index=self._index)
        if _response:
            self._log.info('GET index {} successful.'.format(self._index))
        else:
            self._log.info('index did not exist.')
        return _response

    # ..........................................................................
    def delete_index(self):
        _response = self._es.indices.exists(index=self._index)
        if _response:
            self._log.info('index exists?; response: {}'.format(_response))
            _response = self._es.indices.delete(index=self._index)
            self._log.info('index deleted; response: {}'.format(_response))
        else:
            self._log.info('index did not exist.')

    # ..........................................................................
    def insert_document(self, oid, content):
        # index and doc_type you can customize by yourself
        _response = self._es.index(index=self._index, doc_type=self._doc_type, id=oid, body=content)
        # index will return insert info: like as created is True or False
#       self._log.info(Style.BRIGHT + 'inserted document with oid {}; response:\n'.format(oid) + Fore.GREEN + Style.NORMAL + json.dumps(_response, indent=4))
        _version = _response.get('_version')
        self._log.info('inserted document with oid {}; version: {}'.format(oid, _version))
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

# data = {
#        "author": "Chestermo",
#        "gender": "male",
#        "age": "24",
#        "body_fat": "15%",
#        "interest": ["couch potato", "eat and sleep"]
#    }


# main .........................................................................
_log = Logger("test", Level.INFO)


def main(argv):

    try:

        _level = Level.INFO
        _loader = ConfigLoader(_level)
        filename = 'config.yaml'
        _config = _loader.configure(filename)

        _include_datatype = False
        _jnp = JsonNdParser('|', Level.INFO, _include_datatype)

        _elastic = Elastic(_config, _level)

        if not _elastic.ping():
            raise Exception('could not connect to Elasticsearch service; exiting.')

        _log.info('connected to Elasticsearch service.')

        _elastic.delete_index()
#       sys.exit(0)

        # create index if it doesn't already exist
        _elastic.create_index()

        # import CSV file
        _log.info('parsing data...')
#       _filename = 'pid_log_50.csv'
        _filename = 'pid_log.csv'

        _log.info('parsing file: {}...'.format(_filename))
        # returns a List of strings
        _response = _jnp.parse_file(_filename)
        _log.info('parsed CSV document to {:d} records.'.format(len(_response)))

        _pp = pprint.PrettyPrinter(indent=4)

#       for i in range(len(_response)-1):
        for _document in _response:
#           _log.info('processing document:\n' + Fore.YELLOW + _document)
            _log.info('processing document...')
            # parse OID from JSON
            _json_document = json.loads(_document)

            print(Fore.BLACK)
            _pp.pprint(_json_document)
            print(Style.RESET_ALL)

            if _include_datatype:
                _oid = _json_document.get('row:integer')
            else:
                _oid = _json_document.get('row')
 
#           _log.info('oid [{}]:\n'.format(_oid))
#           _log.info(Fore.MAGENTA + 'oid: {}; JSON {}:'.format(_oid, type(_json_document)))

            _response = _elastic.insert_document(_oid, _json_document)
            _version = _response.get('_version')
            _log.info(Fore.YELLOW + 'created new record with oid {}; version: {}'.format(_oid, _version))

        _log.info('done.')

#           parsed = json.loads(_response)
#       _log.info(Fore.YELLOW + 'response: {}'.format(_pp.pprint(_response)))

#       _version = _response.get('_version')
#       _log.info(Fore.YELLOW + 'version: {}'.format(_version))
#       if _version is not None and _version > 10:
#           _elastic.delete_index()

        _response = _elastic.get_index()
        _log.info(Fore.YELLOW + 'get_index response: {}'.format(_pp.pprint(_response)))

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
    except JsonNdParserException as e:
        _log.error('error converting CSV to JSON: {}'.format(traceback.format_exc()))
    except Exception as e:
        _log.error('error uploading to elasticsearch: {}\n{}'.format(e, traceback.format_exc()))


# call main ....................................................................
if __name__ == "__main__":
    main(sys.argv[1:])

# EOF
