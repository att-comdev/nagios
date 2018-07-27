#!/usr/bin/env python
import requests
import json
import datetime
import time
import argparse
import sys

OK = 0
CRITICAL = 2
UNKNOWN = 3

severity_by_logger_query_str = '''
{
  "query": {
    "bool": {
      "must": {
        "match": {
          "level": "INFO"
        }
      },
      "filter": [
        {
          "range": {
            "@timestamp": {
              "gte": "1503985476144",
              "lte": "1503985776144",
              "format": "epoch_millis"
            }
          }
        },
        {
            "terms": {
                "application": ["elasticsearch"]
            }
        },
        {
            "terms": {
                "_type": ["docker_fluentd"]
            }
        }
      ]
    }
  }
}
'''

severity_by_logger_query_hash = json.loads(severity_by_logger_query_str)


def search(uri, logger, severity_labels, es_type, time_millis_from, time_millis_to):
    query_hash = severity_by_logger_query_hash
    query_hash['query']['bool']['filter'][0]['range']['@timestamp']['gte'] = str(
        time_millis_from)
    query_hash['query']['bool']['filter'][0]['range']['@timestamp']['lte'] = str(
        time_millis_to)
    query_hash['query']['bool']['filter'][1]['terms']['application'] = [logger]
    query_hash['query']['bool']['must']['match']['level'] = severity_labels
    query_hash['query']['bool']['filter'][2]['terms']['_type'] = [es_type]

    request_json = json.dumps(query_hash)
    headers = {'content-type': 'application/json'}
    try:
        response = requests.post(uri, data=request_json, headers=headers, timeout=15)
    except Exception as e:
        print("unable to reach elasticsearch at {}".format(uri))
        sys.exit(UNKNOWN)
    results = json.loads(response.text)
    return results


def evaluate_thresholds(
        results,
        critical_threshold,
        time_range_mins,
        log_level,
        es_type):
    levelVsCount = {}
    messages = []
    exit_code = OK
    prefix = "OK"
    if not results:
        exit_code = OK
        messages.append("No Data available to evaluate")
    else:
        count = results['hits']['total']
        level = log_level
        if count > critical_threshold:
            exit_code = CRITICAL
            prefix = "CRITICAL:"
        messages.append(" {} {} level logs".format(count, level))
        if len(messages) == 0:
            messages.append(
                "No Logs found with level {} in the past {} minutes".format(
                    ",".join(log_level), time_range_mins))
            exit_code = OK
        else:
            messages.append(" in the last {} minutes".format(time_range_mins))
            messages.append("Pods/Hosts: ")
            for hit in results['hits']['hits']:
                if 'log' in hit['_source']:
                    messages.append(hit['_source']['kubernetes']['pod_name'])
                else:
                    messages.append(hit['_source']['hostname'])

    message = "{}:{}".format(prefix, ",".join(messages).encode('utf-8').strip())
    return exit_code, message


if __name__ == '__main__':
    parser = argparse.ArgumentParser(
        description='searches for log levels and alerts')
    parser.add_argument(
        '--es_url',
        metavar='es_url',
        type=str,
        required=True,
        help='url with port for elasticsearch rest api')
    parser.add_argument(
        '--logger',
        metavar='logger',
        type=str,
        required=True,
        help='Logger search term filter')
    parser.add_argument(
        '--range_mins',
        metavar='range_mins',
        type=int,
        required=False,
        default=10,
        help='Number of minutes to look back in the past')
    parser.add_argument(
        '--alert_level',
        metavar='alert_level',
        type=str,
        required=False,
        default='ERROR',
        help='Log level to alert upon')
    parser.add_argument(
        '--critical',
        metavar='critical',
        type=int,
        required=True,
        help='Number of logs at alert_level to alert critical')
    parser.add_argument(
        '--es_type',
        metavar='es_type',
        type=str,
        required=True,
        help='Elasticsearch document type')
    args, unknown = parser.parse_known_args()

    time_millis_to = int(datetime.datetime.now().strftime("%s")) * 1000
    time_millis_from = time_millis_to - (args.range_mins * 60 * 1000)
    es_search_url = "{}/_search".format(args.es_url)
    results = search(
        es_search_url,
        args.logger,
        args.alert_level,
        args.es_type,
        time_millis_from,
        time_millis_to
        )
    exit_code, message = evaluate_thresholds(
        results, args.critical, args.range_mins, args.alert_level, args.es_type)
    print message
    sys.exit(exit_code)
