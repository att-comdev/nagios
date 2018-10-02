#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Search Elasticsearch using simple query patterns"""

from __future__ import print_function

import sys

import argparse
import datetime
import json
from pprint import pprint
import requests

def check_range(value):
    """validate range"""
    minutes = int(value)
    type_err_str = ('%s is an invalid search time range.' +
                    ' Valid values are between 1 and 1440(1 day) minutes.')
    if minutes < 1 or minutes > 1440:
        raise argparse.ArgumentTypeError(type_err_str % value)
    return minutes

def check_match(value):
    """validate match clauses"""
    type_err_str = ('%s is an invalid match clause(s) list.' +
                    ' Valid format is a comma separated list of' +
                    ' field name and value pairs.' +
                    ' ex. field1:value1,field2:value2,...')
    try:
        match_fields = dict(item.split(':') for item in value.split(','))
        return match_fields
    except:
        raise argparse.ArgumentTypeError(type_err_str % value)

def setup_parser(parser):
    """setup argparse parser with arguments and help texts"""
    range_help = ('relative time range between now and x minutes ago.' +
                  ' must be between 1 <= x <=1440 minutes, default is 60')
    endpoint_help = 'elasticsearch API service endpoint url'
    fields_help = 'fields to perform the parsed simple query against'
    query_help = 'elasticsearch simple query string'
    match_help = ('elasticsearch match clause(s), in the format of' +
                  ' comma separated list of field name and value pairs.' +
                  ' ex. field1:value1,field2:value2,...')
    parser.add_argument('usr')
    parser.add_argument('pwd')
    parser.add_argument('endpoint', help=endpoint_help)
    parser.add_argument('index', help='elasticsearch index')
    parser.add_argument('index_type', help='elasticsearch index type')
    parser.add_argument('fields', help=fields_help)
    parser.add_argument('query', help=query_help)
    parser.add_argument('--match', type=check_match, help=match_help)
    parser.add_argument('--range', type=check_range, default=60,
                        help=range_help)
    parser.add_argument('--debug', action='store_true')

def main():
    """search elasticsearch index with given patterns and return the
       original search result from the elasticsearch api"""
    desc = ('Elasticsearch pattern search using simple query.' +
            ' ex. \"query_es.py usr pwd endpoint index index_type' +
            ' fields simplequery --match f1:v1,f2:v2 --range 60 --debug\"')
    parser = argparse.ArgumentParser(description=desc)
    setup_parser(parser)
    args = parser.parse_args()

    lt_time = datetime.datetime.utcnow()
    gte_time = lt_time - datetime.timedelta(minutes=(int(args.range)))
    log_lt = args.index + "-" + lt_time.strftime('%Y.%m.%d')
    log_gte = args.index + "-" + gte_time.strftime('%Y.%m.%d')

    if log_lt == log_gte:
        es_index = log_lt
    else:
        es_index = log_lt + ',' + log_gte

    data = {
        "inline" : {
            "query": {
                "bool": {
                    "must": [
                        {
                            "range": {
                                "@timestamp": {
                                    "lt": "{{lt_timestamp}}",
                                    "gte": "{{gte_timestamp}}"
                                }
                            }
                        },
                        {
                            "simple_query_string" : {
                                "fields" : ["{{fields}}"],
                                "query" : "{{query}}"
                            }
                        }
                    ]
                },
            },
            "size": 10
        }
    }

    if args.match:
        for key in args.match:
            element = {"match": {key: args.match[key]}}
            data['inline']['query']['bool']['must'].append(element)

    params = {}
    params['lt_timestamp'] = lt_time.isoformat()
    params['gte_timestamp'] = gte_time.isoformat()
    params['gte_timestamp'] = gte_time.isoformat()
    params['fields'] = args.fields
    params['query'] = args.query
    data['params'] = params

    url = (args.endpoint + '/' + es_index + '/' +
           args.index_type + '/' + '_search/template')

    headers = {"Content-Type": "application/json"}

    if args.debug:
        print('query url:\n' + url)
        print('query data:')
        pprint(data)

    response = requests.post(url, data=json.dumps(data), headers=headers,
                             auth=(args.usr, args.pwd))
    pprint(response.json())

if __name__ == '__main__':
    sys.exit(main())
