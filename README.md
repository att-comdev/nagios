Prometheus aware Nagios core 4 image
============

Prometheus aware nagios core 4 image that auto-discovers prometheus hosts and provides plugins to query prometheus alerts.

## Environment

* PROM_METRICS_SERVICE
  - Prometheus API host (ip address or vip with port)
  - available in container as nagios macro $USER2$

* CEPH_METRICS_SERVICE
  - CEPH exporter endpoint (example: http://192.168.0.1:9283/metrics)
  - available in container as nagios macro $USER3$

* SNMP_NOTIF_PRIMARY_TARGET_WITH_PORT
  - primary SNMP notification target (example: 192.168.0.1:15132)
  - available in container as nagios macro $USER4$

* SNMP_NOTIF_SECONDARY_TARGET_WITH_PORT
  - secondary SNMP notification target (example: 192.168.0.2:15132)
  - available in container as nagios macro $USER5$

* REST_NOTIF_PRIMARY_TARGET_URL
  - primary REST notification target (example: http://primary.com:3904/events/AIC-INFRA-NAGIOS-ALARMS)
  - available in container as nagios macro $USER6$

* REST_NOTIF_SECONDARY_TARGET_URL
  - secondary REST notification target (example: http://secondary.com:3904/events/AIC-INFRA-NAGIOS-ALARMS)
  - available in container as nagios macro $USER7$
