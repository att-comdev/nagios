#!/usr/bin/env bash
#
# Arguments:
# $1 = host_name
# $2 = service_description (Description of the service)
# $3 = return_code (An integer that determines the state
#       of the service check, 0=OK, 1=WARNING, 2=CRITICAL,
#       3=UNKNOWN).
# $4 = plugin_output (A text string that should be used
#       as the plugin output for the service check)
# $5 = monitoring hostname fqdn
# $6 = primary REST API destination with scheme, host, port, api path to POST event to
# $7 = standby REST API destination with scheme, host, port, api path to POST event to
# Example payload sent out:
#{
#    "SvcEvent":{
#        "SvcHostname":"testhostwithissue.x.y.com",
#        "SvcDesc":"Service_nova-compute",
#        "SvcStateID":"2",
#        "SvcOutput":"nova-compute stop/waiting",
#        "MonitoringHostName":"nagiosserver.x.y.com"
#    }
#}

PAYLOAD="{\"SvcEvent\":{\"SvcHostname\":\"$1\",\"SvcDesc\":\"$2\",\"SvcStateID\":\"$3\",\"SvcOutput\":\"$4\",\"MonitoringHostName\":\"$5\"}}"

if [ ! -z "$6" ]; then
  nohup curl --max-time 10 "$6" -H 'Content-Type: application/json' -d "$PAYLOAD" > /dev/null 2>&1 &

  if [ ! -z "$7" ]; then
    nohup curl --max-time 10 "$7" -H 'Content-Type: application/json' -d "$PAYLOAD" > /dev/null 2>&1 &
  fi
fi
