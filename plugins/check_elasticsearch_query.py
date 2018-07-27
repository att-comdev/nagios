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
    "filtered": {
      "query": {
        "query_string": {
          "query": "*",
          "analyze_wildcard": true
        }
      },
      "filter": {
        "bool": {
          "must": [
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
                "kubernetes.labels.application": [
                  "nova"
                ]
              }
            },
            {
              "terms": {
                "severity_label": [
                  "ERROR",
                  "CRITICAL"
                ]
              }
            }
          ],
          "must_not": []
        }
      }
    }
  },
  "size": 5,
  "aggs": {
    "2": {
      "terms": {
        "field": "severity_label",
        "size": 5,
        "order": {
          "_count": "desc"
        }
      }
    }
  }
}
'''

severity_by_logger_query_hash = json.loads(severity_by_logger_query_str)


def search(uri, logger, severity_labels, time_millis_from, time_millis_to):
    query_hash = severity_by_logger_query_hash
    query_hash['query']['filtered']['filter']['bool']['must'][0]['range']['@timestamp']['gte'] = str(
        time_millis_from)
    query_hash['query']['filtered']['filter']['bool']['must'][0]['range']['@timestamp']['lte'] = str(
        time_millis_to)
    query_hash['query']['filtered']['filter']['bool']['must'][1]['terms']['kubernetes.labels.application'] = [logger]
    query_hash['query']['filtered']['filter']['bool']['must'][2]['terms']['severity_label'] = severity_labels

    request_json = json.dumps(query_hash)
    try:
        response = requests.post(uri, data=request_json, timeout=15)
    except Exception as e:
        print("unable to reach elasticsearch at {}".format(uri))
        sys.exit(UNKNOWN)
    results = json.loads(response.text)
    return results


def evaluate_thresholds(
        results,
        critical_threshold,
        time_range_mins,
        log_levels):
    levelVsCount = {}
    messages = []
    exit_code = OK
    prefix = "OK"
    if not results \
            or 'aggregations' not in results \
            or '2' not in results['aggregations'] \
            or 'buckets' not in results['aggregations']['2']:
        exit_code = OK
        messages.append("No Data available to evaluate")
    else:
        for bucket in results['aggregations']['2']['buckets']:
            count = bucket['doc_count']
            level = bucket['key']
            if count > critical_threshold:
                exit_code = CRITICAL
                prefix = "CRITICAL:"
            messages.append(" {} {} level logs".format(count, level))
        if len(messages) == 0:
            messages.append(
                "No Logs found with levels {} in the past {} minutes".format(
                    ",".join(log_levels), time_range_mins))
            exit_code = OK
        else:
            messages.append(" in the last {} minutes".format(time_range_mins))
            messages.append("Samples: ")
            for hit in results['hits']['hits']:
                messages.append(hit['_source']['Payload'])

    message = "{}:{}".format(prefix, ",".join(messages))
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
        '--alert_levels',
        metavar='alert_levels',
        type=str,
        required=False,
        default='ERROR,CRITICAL',
        help='Log levels to alert upon')
    parser.add_argument(
        '--critical',
        metavar='critical',
        type=int,
        required=True,
        help='Number of logs at alert_level to alert ciritcal')
    args, unknown = parser.parse_known_args()

    time_millis_to = int(datetime.datetime.now().strftime("%s")) * 1000
    time_millis_from = time_millis_to - (args.range_mins * 60 * 1000)
    index = "log-{}".format(time.strftime("%Y.%m.%d"))
    es_search_url = "{}/{}/_search".format(args.es_url, index)
    results = search(
        es_search_url,
        args.logger,
        args.alert_levels.split(","),
        time_millis_from,
        time_millis_to)
    exit_code, message = evaluate_thresholds(
        results, args.critical, args.range_mins, args.alert_levels.split(","))
    print message
    sys.exit(exit_code)
