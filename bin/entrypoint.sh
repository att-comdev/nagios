#!/bin/bash

# Apply environment variables
sed -ri -e 's/(^\s+email\s+)\S+(.*)/\1'${NAGIOSADMIN_EMAIL}'\2/' ${NAGIOS_HOME}/etc/objects/contacts.cfg
sed -i -e 's/=nagiosadmin$/='*'/' ${NAGIOS_HOME}/etc/cgi.cfg
echo "\$USER1\$=${NAGIOS_PLUGIN_DIR}" >> ${NAGIOS_HOME}/etc/resource.cfg
if [ -n "$PROMETHEUS_SERVICE" ]; then
  echo "\$USER2\$=${PROMETHEUS_SERVICE}" >> ${NAGIOS_HOME}/etc/resource.cfg
fi
if [ -n "$CEPH_METRICS_SERVICE" ]; then
  echo "\$USER3$=${CEPH_METRICS_SERVICE}" >> ${NAGIOS_HOME}/etc/resource.cfg
fi
if [ -n "$SNMP_NOTIF_PRIMARY_TARGET_WITH_PORT" ]; then
  echo "\$USER4$=${SNMP_NOTIF_PRIMARY_TARGET_WITH_PORT}" >> ${NAGIOS_HOME}/etc/resource.cfg
fi
if [ -n "$SNMP_NOTIF_SECONDARY_TARGET_WITH_PORT" ]; then
  echo "\$USER5$=${SNMP_NOTIF_SECONDARY_TARGET_WITH_PORT}" >> ${NAGIOS_HOME}/etc/resource.cfg
fi
if [ -n "$REST_NOTIF_PRIMARY_TARGET_URL" ]; then
  echo "\$USER6$=${REST_NOTIF_PRIMARY_TARGET_URL}" >> ${NAGIOS_HOME}/etc/resource.cfg
fi
if [ -n "$REST_NOTIF_SECONDARY_TARGET_URL" ]; then
  echo "\$USER7$=${REST_NOTIF_SECONDARY_TARGET_URL}" >> ${NAGIOS_HOME}/etc/resource.cfg
fi
if [ -n "$SNMP_COMMUNITY_STRING" ]; then
  echo "\$USER8$=${SNMP_COMMUNITY_STRING}" >> ${NAGIOS_HOME}/etc/resource.cfg
else
  UUID=$(cat /proc/sys/kernel/random/uuid)
  echo "\$USER8$=${UUID}" >> ${NAGIOS_HOME}/etc/resource.cfg
fi


touch ${NAGIOS_HOME}/etc/objects/prometheus_discovery_objects.cfg
chown nagios ${NAGIOS_HOME}/etc/objects/prometheus_discovery_objects.cfg

sed -i -e 's/APACHE_FRONTEND_PORT/'${APACHE_FRONTEND_PORT}'/' /etc/apache2/ports.conf
sed -i -e 's/APACHE_FRONTEND_SECURE_PORT/'${APACHE_FRONTEND_SECURE_PORT}'/' /etc/apache2/ports.conf

/etc/init.d/apache2 restart
/etc/init.d/nagios stop

exec /opt/nagios/bin/nagios /opt/nagios/etc/nagios.cfg
