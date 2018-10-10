# !/usr/bin/env python
# -*- coding: utf-8 -*-
"""Search elasticsearch using simple query patterns and field matches,
   and evaluate the results against the alert threshold"""

from __future__ import print_function

import sys

import argparse
import datetime
import json
from pprint import pprint
import requests

from aicmonutil import AICMonUtil

def check_range(value):
    """validate range"""
    minutes = int(value)
    type_err_str = ('%s is an invalid search time range.' +
                    ' Valid values are between 1 and 1440(1 day) minutes.')
    if minutes < 1 or minutes > 1440:
        raise argparse.ArgumentTypeError(type_err_str % value)
    return minutes

def check_threshold(value):
    """validate threshold"""
    threshold = int(value)
    type_err_str = ('%s is an invalid threshold' +
                    ' Valid threshold is > 0')
    if threshold < 1:
        raise argparse.ArgumentTypeError(type_err_str % value)
    return threshold

def check_match(value):
    """validate match clauses"""
    if not value: #tolerate empty match clause
        return
    type_err_str = ('%s is an invalid match clause(s) list.' +
                    ' Valid format is a comma separated list of' +
                    ' field name and value pairs.' +
                    ' ex. field1:value1,field2:value2,...')
    try:
        match_fields = dict(item.split(':') for item in value.split(','))
        return match_fields
    except:
        raise argparse.ArgumentTypeError(type_err_str % value)

def setup_argparse(parser):
    """setup argparse parser with arguments and help texts"""
    range_help = ('relative time range between now and x minutes ago.' +
                  ' must be between 1 <= x <=1440 minutes, default is 60')
    endpoint_help = 'elasticsearch API service endpoint url'
    fields_help = 'fields to perform the parsed simple query against'
    query_help = 'elasticsearch simple query string'
    match_help = ('elasticsearch match clause(s), in the format of' +
                  ' comma separated list of field name and value pairs.' +
                  ' ex. field1:value1,field2:value2,...')
    ok_msg_help = ('OK status display message')
    critical_msg_help = ('Critical status display message')
    critical_threshold_help = ('Status is Critical if the' +
                               ' number of hits >= the threshold')
    parser.add_argument('endpoint', help=endpoint_help)
    parser.add_argument('index', help='elasticsearch index')
    parser.add_argument('index_type', help='elasticsearch index type')
    parser.add_argument('fields', help=fields_help)
    parser.add_argument('query', help=query_help)
    parser.add_argument('ok_msg', help=ok_msg_help)
    parser.add_argument('critical_msg', help=critical_msg_help)
    parser.add_argument('critical_threshold', type=check_threshold, help=critical_threshold_help)
    parser.add_argument('--usr')
    parser.add_argument('--pwd')
    parser.add_argument('--match', type=check_match, help=match_help)
    parser.add_argument('--range', type=check_range, default=60,
                        help=range_help)
    parser.add_argument('--debug', action='store_true')

def get_index_name(args, lt_time, gte_time):
    """build the index name(s) based on the inputs and current time"""
    log_lt = args.index + '-' + lt_time.strftime('%Y.%m.%d')
    log_gte = args.index + '-' + gte_time.strftime('%Y.%m.%d')

    if log_lt == log_gte:
        es_index = log_lt
    else:
        es_index = log_lt + ',' + log_gte
    return es_index

def evaluate_results(response, args):
    """evaluate the results of the query against the threshold to
      determine the nagios service status"""
    if not AICMonUtil.is_success(response) or not response.json():
        AICMonUtil.service_unknown('Unknown results found. ' + response.text)
    elif (not response.json()['hits'] or
          int(response.json()['hits']['total']) < 0):
        AICMonUtil.service_unknown('Unknown results found. ' + str(response.json()))

    if args.debug:
        pprint(response.json())

    results = response.json()
    hits = results['hits']['total']

    message = ('Found ' + str(hits) + '%s' +
               str(args.critical_threshold) + '(threshold) occurrences' +
               ' within the last ' + '%s' + ' minute(s). ')

    if hits >= args.critical_threshold:
        AICMonUtil.service_critical((message % (' >= ', args.range)) + args.critical_msg)
    else:
        AICMonUtil.service_ok((message % (' < ', args.range)) + args.ok_msg)

def main():
    """search elasticsearch index with given patterns and return the
       original search result from the elasticsearch api"""
    desc = ('Elasticsearch pattern search using simple query.' +
            ' ex. \"query_es.py usr pwd endpoint index index_type' +
            ' fields simplequery --match f1:v1,f2:v2 --range 60 --debug\"')
    parser = argparse.ArgumentParser(description=desc)
    setup_argparse(parser)
    args = parser.parse_args()

    lt_time = datetime.datetime.utcnow()
    gte_time = lt_time - datetime.timedelta(minutes=(int(args.range)))

    es_index = get_index_name(args, lt_time, gte_time)

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
            element = {'match': {key: args.match[key]}}
            data['inline']['query']['bool']['must'].append(element)

    params = {}
    params['lt_timestamp'] = lt_time.isoformat()
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

    try:
        if args.usr and args.pwd:
            response = requests.post(url, data=json.dumps(data), headers=headers,
                                     auth=(args.usr, args.pwd))
        else:
            response = requests.post(url, data=json.dumps(data), headers=headers)
    except requests.exceptions.RequestException as req_ex:
        AICMonUtil.service_unknown('Unexpected Error Occurred. ' + str(req_ex))

    evaluate_results(response, args)

if __name__ == '__main__':
    sys.exit(main())
