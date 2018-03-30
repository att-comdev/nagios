Prometheus aware Nagios core 4 image
============

Prometheus aware nagios core 4 image that auto-discovers prometheus hosts and provides plugins to query prometheus alerts.

## Environment

* PROM_METRICS_SERVICE
  - Prometheus API host (ip address or vip with port)

* CEPH_METRICS_SERVICE
  - CEPH exporter endpoint (example: 192.168.0.1:9283/metrics)
