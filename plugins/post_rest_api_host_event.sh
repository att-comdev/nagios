#!/usr/bin/env bash
#
# Arguments:
# $1 = host_name
# $2 = HostStatID A number that corresponds to the current state of the host: 0=UP, 1=DOWN, 2=UNREACHABLE.
# $3 = HOSTOUTPUT The first line of text output from the last host check (i.e. "Ping OK").
# $4 = monitoring hostname fqdn
# $5 = primary REST API with scheme, host, port, api path to POST event to
# $6 = standby REST API with scheme, host, port, api path to POST event to
# Example payload sent out:
#{
#    "HostEvent":{
#        "Hostname":"hostwithevent.y.x.com",
#        "HostStateID":"2",
#        "HostOutput":"PING CRITICAL - Packet loss = 100%",
#        "MonitoringHostName":"nagioshost.x.y.com"
#    }
#}

PAYLOAD="{\"HostEvent\":{\"Hostname\":\"$1\",\"HostStateID\":\"$2\",\"HostOutput\":\"$3\",\"MonitoringHostName\":\"$4\"}}"
if [ ! -z "$5" ]; then
  nohup curl --max-time 10 "$5" -H 'Content-Type: application/json' -d "$PAYLOAD" > /dev/null 2>&1 &
  if [ ! -z "$6" ]; then
    nohup curl --max-time 10 "$6" -H 'Content-Type: application/json' -d "$PAYLOAD" > /dev/null 2>&1 &
  fi
fi
