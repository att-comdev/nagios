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
from datetime import datetime, timedelta
import time
import json
import re
from pprint import pprint
import requests
from nagiosutil import NagiosUtil


def check_bool(value):
    """validate range"""
    return value.lower() in [ 'true', 'yes', 'on', 't', 'y',  '1']

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
    if not value:  # tolerate empty match clause
        return
    try:
        match_fields = dict(item.split(':') for item in value.split(','))
        return match_fields
    except BaseException:
        raise argparse.ArgumentTypeError('%s is an invalid match clause(s) list.'
                                         ' Valid format is a comma separated'
                                         ' list of field name and value pairs.'
                                         ' ex. field1:value1,field2:value2,...'
                                         % value)

def check_datetime(value):
    the_datetime = None
    if not re.match(r'\d{4}\-\d{2}\-\d{2}T\d{2}\:\d{2}\:\d{2}(\.\d+){0,1}', value.strip()):
        raise argparse.ArgumentTypeError('%s is an invalid date format, expect YYYY-mm-dd' % value)
    else:
        the_datetime = datetime.strptime(value, '%Y-%m-%dT%H:%M:%S')
    return the_datetime

def check_date(value):
    """validate date (only, no time) in standard format """
    the_date = None
    if not re.match(r'\d{4}\-\d{2}\-\d{2}', value.strip()):
        raise argparse.ArgumentTypeError('%s is an invalid date format, expect YYYY-mm-dd' % value)
    else:
        the_date = datetime.strptime(value, '%Y-%m-%d')
    return the_date

def check_timezone(value):
    """validate timezone specification +/-hh:mm """
    text = value.strip()

    if not re.match(r'(\+|\-){1}\d{2}\:\d{2}', text):
        raise argparse.ArgumentTypeError('%s is an invalid timezone format, expect +/-hh:mm' % text)
    return text

def get_utc_timezone():
    return -1 * time.altzone / (60 * 60)

def get_utc_timezone_str():
    text = ''
    offset = get_utc_timezone()
    if offset < 0:
        text = '-'
    else:
        text = '+'
    offset = abs(offset)
    return text + format(offset, '02d') + ':00'


def setup_argparse(parser):
    """setup argparse parser with arguments and help texts"""

    pprint('beginning of setup_argparse')
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

    parser.add_argument('es_index_name', help='elasticsearch index name (mandatory, used to select es index file')
    parser.add_argument('es_index_type', help='elasticsearch index type (mandatory es index parameter)')
    parser.add_argument('ok_msg', help='OK status display message')
    parser.add_argument('critical_msg', help='Critical status display message')
    parser.add_argument('critical_threshold', type=check_threshold, help=critical_threshold_help)
    parser.add_argument('range', type=check_range, default=5,help=range_help)

    parser.add_argument('@@search_timestamp', type=check_datetime, help='timestamp to use for search (optional, defaults to now)')
    parser.add_argument('@@search_timezone', type=check_timezone, default='-04:00', help='timezone to use for search (optional, defaults to +/-00:00)')
    parser.add_argument('@@es_index_date', type=check_date, help='elasticsearch index type (mandatory, but =null to not use it!  used to build index file name..dated - defaults to now date)')

    parser.add_argument('@@only_non_att_users', type=check_bool, help='show only cases where there are non att-users (default=false)')

    parser.add_argument('@@usr')
    parser.add_argument('@@pwd')
    parser.add_argument('@@debug', action='store_true')
    pprint('end of setup_argparse')


def build_url_index_section(index_name, base_date, offset_array):
    """ for this use-case -> always work with two index files: 1) index of the day (i.e. gte_time) and 2) index of prior day """

    text_array = []
    for day_offset in offset_array:
        offset_date = base_date  + timedelta(days=day_offset)
        date_text = index_name + '-' + offset_date.strftime('%Y.%m.%d')
        text_array.append(date_text)

    merged_text = ",".join(text_array)
    return merged_text

def adjust_missing_index_date(args, ref_datetime):
    """ if es index date is missing, use the search date (only date) as value  """
    if not args.es_index_date:
        args.es_index_date = ref_datetime.date()


def evaluate_results(response, args):
    """evaluate the results of the query against the threshold to
      determine the nagios service status"""
    if (not response or not hasattr(response, 'status_code')
            or response.status_code < 200 or response.status_code >= 400
            or not response.json()):
        NagiosUtil.service_unknown('Unexpected results found. ' + response.text)
    elif (not response.json()['hits']
          or int(response.json()['hits']['total']) < 0):
        NagiosUtil.service_unknown('Unexpected results found. ' + str(response.json()))

    if args.debug:
        pprint(response.json())

    results = response.json()
    hits = results['hits']['total']

    result_array = results['hits']['hits']
    result_string =  build_detailed_string_from_results(args, result_array)

    message = ('Found %s >= %s(threshold) occurrences'
               ' within the last %s minute(s). %s results: %s')

    if hits >= args.critical_threshold:
        NagiosUtil.service_critical(message % (str(hits), args.critical_threshold,
                                               args.range, args.critical_msg, result_string))
    else:
        NagiosUtil.service_ok(args.ok_msg)


def build_detailed_string_from_results(args, result_array):
    returned_string = ""

    for i in range(len(result_array)):
        jobj = result_array[i]
        jsource = jobj['_source']
        the_time = jsource['@timestamp']
        the_reason = jsource['log']

        the_who = ''
        the_who2 = ''
        match_obj = re.match(r'.*\: from user\: (\S+)\: to user\: (\S+).*', the_reason, re.M|re.I)
        if match_obj:
            the_who = match_obj.group(1)
            if the_who and the_who.lower() == 'root':
                the_who = ''

            the_who2 = match_obj.group(2)
            if the_who2 and the_who2.lower() == 'root':
                the_who2 = ''

        if args.only_non_att_users:
            if (not re.match(r'\w{2}\d{4}',the_who)) or (not re.match(r'\w{2}\d{4}',the_who2)):
                returned_string += ( '( ' + the_time + ' ; ' + the_who + ' ; ' + the_who2 + ' ; ' + the_reason + ' ) ' )
        else:
            returned_string += ( '( ' + the_time + ' ; ' + the_who + ' ; ' + the_who2 + ' ; ' + the_reason + ' ) ' )

    return returned_string

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
    parser = argparse.ArgumentParser(prefix_chars='@', description=desc)
    setup_argparse(parser)

    pprint('before parser.parse_args')
    args = parser.parse_args()
    pprint('after parser.parse_args')

    # find search date, etheir noew or parameter timestamp
    lt_time = datetime.utcnow()
    if args.search_timestamp:
        lt_time = args.search_timestamp

    gte_time = lt_time - timedelta(minutes=(int(args.range)))

    # if es_index_date was not passed as parameter, then  create it and use search_timestamp as value
    adjust_missing_index_date(args, lt_time)

    # if args.search_timezone was not specified on the command-line, then read local timezone
    #pprint("=====> datetime.tzinfo" + datetime.tzinfo)
    if not args.search_timezone:
        args.search_timezone = get_utc_timezone_str()
        pprint("=====> args.search_timezone" + args.search_timezone)

    data = {
        "source": {
            "explain": "true",
            "_source": [ "log", "@timestamp"],
            "query": {
                "bool": {
                    "filter": {
                        "range": {
                            "@timestamp" : {
                                "gte": "{{target_gte_time}}",
                                "lt": "{{target_lt_time}}",
                                "time_zone": "{{target_timezone}}"
                            }
                        }
                    },
                    "must": {
                        "match": {
                            "{{target_field}}" : {
                                "query": "{{target_value}}",
                                "type": "phrase"
                            }
                        }
                    }
                }
            },
            "size" : "{{want_size}}"
        }
    }

    params = {}
    params['target_lt_time'] = lt_time.strftime("%Y-%m-%dT%H:%M:%S") + '.0'
    params['target_gte_time'] = gte_time.strftime("%Y-%m-%dT%H:%M:%S") + '.0'
    params['target_timezone'] = args.search_timezone

    params['target_field'] = "log"
    params['target_value'] = " nologin: allowed: from user:"
    params['want_size'] = 25

    data['params'] = params

    url = (args.endpoint + '/' + build_url_index_section(args.es_index_name, args.es_index_date, [0, -1] ) + '/'
           + args.es_index_type + '/' + '_search/template')

    if args.debug:
        pprint('index name: ' + args.es_index_name)
        pprint('index type: ' + args.es_index_type)
        pprint('index date: ' + args.es_index_date.strftime("%Y-%m-%d"))
        pprint('lt_time: ' + lt_time.strftime("%Y-%m-%dT%H:%M:%S") )
        pprint('gte_time: ' + gte_time.strftime("%Y-%m-%dT%H:%M:%S") )
        pprint('search_timezone: ' + args.search_timezone)
        pprint('range: ' + str(args.range))
        pprint('critial_threshold: ' + str(args.critical_threshold))

        pprint('query url: ' + url)
        pprint('query data:')
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


