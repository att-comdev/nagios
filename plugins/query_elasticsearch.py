#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# Copyright 2017 The Openstack-Helm Authors.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#   http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#
"""Query elasticsearch using a combination of simple query pattern,
   field matches, and/or query clause and evaluate the results against
   the alert threshold"""

from __future__ import print_function

import sys

import argparse
import datetime
import json
from pprint import pprint
import requests

from nagiosutil import NagiosUtil

def check_range(value):
    """validate range"""
    minutes = int(value)
    if minutes < 1 or minutes > 1440:
        raise argparse.ArgumentTypeError('%s is an invalid search time range.'
                                         ' Valid values are between 1 and 1440'
                                         '(1 day) minutes.' % value)
    return minutes

def check_threshold(value):
    """validate threshold"""
    threshold = int(value)
    if threshold < 1:
        raise argparse.ArgumentTypeError('%s is an invalid threshold'
                                         ' Valid threshold is > 0' % value)
    return threshold

def check_match(value):
    """validate match clauses"""
    if not value: # tolerate empty match clause
        return
    try:
        match_fields = dict(item.split(':') for item in value.split(','))
        return match_fields
    except:
        raise argparse.ArgumentTypeError('%s is an invalid match clause(s) list.'
                                         ' Valid format is a comma separated'
                                         ' list of field name and value pairs.'
                                         ' ex. field1:value1,field2:value2,...'
                                         % value)

def setup_argparse(parser):
    """setup argparse parser with arguments and help texts"""
    range_help = ('relative time range between now and x minutes ago.'
                  ' must be between 1 <= x <=1440 minutes, default is 5')
    endpoint_help = 'elasticsearch API service endpoint url'
    simple_query_fields_help = ('fields to perform the parsed simple query'
                                ' against')
    match_help = ('elasticsearch match clause(s), in the format of'
                  ' comma separated list of field name and value pairs.'
                  ' ex. field1:value1,field2:value2,...')
    critical_threshold_help = ('Status is Critical if the'
                               ' number of hits >= the threshold')

    parser.add_argument('endpoint', help=endpoint_help)
    parser.add_argument('index', help='elasticsearch index')
    parser.add_argument('index_type', help='elasticsearch index type')
    parser.add_argument('ok_msg', help='OK status display message')
    parser.add_argument('critical_msg', help='Critical status display message')
    parser.add_argument('critical_threshold', type=check_threshold,
                        help=critical_threshold_help)
    parser.add_argument('--query_file', help='elasticsearch query file name')
    parser.add_argument('--query_clause', help='elasticsearch query clause name')
    parser.add_argument('--simple_query', help='elasticsearch simple query str')
    parser.add_argument('--simple_query_fields', help=simple_query_fields_help)
    parser.add_argument('--match', type=check_match, help=match_help)
    parser.add_argument('--range', type=check_range, default=5,
                        help=range_help)
    parser.add_argument('--usr')
    parser.add_argument('--pwd')
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
    if (not response or not hasattr(response, 'status_code')
            or response.status_code < 200 or response.status_code >= 400 or
            not response.json()):
        NagiosUtil.service_unknown('Unexpected results found. ' + response.text)
    elif (not response.json()['hits'] or
          int(response.json()['hits']['total']) < 0):
        NagiosUtil.service_unknown('Unexpected results found. ' + str(response.json()))

    if args.debug:
        pprint(response.json())

    results = response.json()
    hits = results['hits']['total']

    message = ('Found %s >= %s(threshold) occurrences'
               ' within the last %s minute(s). %s')

    if hits >= args.critical_threshold:
        NagiosUtil.service_critical(message % (str(hits), args.critical_threshold,
                                               args.range, args.critical_msg))
    else:
        NagiosUtil.service_ok(args.ok_msg)

def main():
    """Query elasticsearch using a combination of simple query pattern,
    field matches, and/or query clause, then evaluate the results against
    the alert threshold, and finally return a status to nagios."""

    desc = ('Elasticsearch query using a combination of simple query pattern,'
            ' field matches, and/or query clause. Evaluate the results'
            ' against the alert threshold, and return a status to'
            ' nagios.'
            ' ex. \"query_elasticsearch.py endpoint index index_type'
            ' ok_msg critical_msg critical_threshold'
            ' --query_file query_file_name'
            ' --simple_query simple_query'
            ' --simple_query_fields fields'
            ' --match f1:v1,f2:v2 --range 5 --debug\"')
    parser = argparse.ArgumentParser(description=desc)
    setup_argparse(parser)
    args = parser.parse_args()

    lt_time = datetime.datetime.utcnow()
    gte_time = lt_time - datetime.timedelta(minutes=(int(args.range)))

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
                        }
                    ]
                }
            },
            "size": 10
        }
    }

    simple_query_clause = {
        "simple_query_string" : {
            "fields" : ["{{fields}}"],
            "query" : "{{query}}"
        }
    }

    if args.query_file and args.query_clause:
        with open(args.query_file, 'r') as queryfile:
            clause = json.loads(queryfile.read())[args.query_clause]
            data['inline']['query']['bool']['must'].append(clause)

    if args.match:
        for key in args.match:
            element = {'match': {key: args.match[key]}}
            data['inline']['query']['bool']['must'].append(element)

    params = {}
    params['lt_timestamp'] = lt_time.isoformat()
    params['gte_timestamp'] = gte_time.isoformat()

    if args.simple_query and args.simple_query_fields:
        data['inline']['query']['bool']['must'].append(simple_query_clause)
        params['fields'] = args.simple_query_fields
        params['query'] = args.simple_query

    data['params'] = params

    url = (args.endpoint + '/' + get_index_name(args, lt_time, gte_time) + '/' +
           args.index_type + '/' + '_search/template')

    if args.debug:
        print('query url:\n' + url)
        print('query data:')
        pprint(data)

    try:
        if args.usr and args.pwd:
            response = requests.post(url, data=json.dumps(data),
                                     headers={"Content-Type": "application/json"},
                                     auth=(args.usr, args.pwd))
        else:
            response = requests.post(url, data=json.dumps(data),
                                     headers={"Content-Type": "application/json"})
    except requests.exceptions.RequestException as req_ex:
        NagiosUtil.service_unknown('Unexpected Error Occurred. ' + str(req_ex))

    evaluate_results(response, args)

if __name__ == '__main__':
    sys.exit(main())
