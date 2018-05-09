#!/bin/bash

# Apply environment variables
sed -ri -e 's/(^\s+email\s+)\S+(.*)/\1'${NAGIOSADMIN_EMAIL}'\2/' ${NAGIOS_HOME}/etc/objects/contacts.cfg
sed -i -e 's/nagiosadmin/'${NAGIOSADMIN_USER}'/' ${NAGIOS_HOME}/etc/objects/contacts.cfg
sed -i -e 's/=nagiosadmin$/='${NAGIOSADMIN_USER}'/' ${NAGIOS_HOME}/etc/cgi.cfg
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

if [ ! -f ${NAGIOS_HOME}/etc/htpasswd.users ] ; then
  htpasswd -bc ${NAGIOS_HOME}/etc/htpasswd.users ${NAGIOSADMIN_USER} "${NAGIOSADMIN_PASS}"
  chown -R ${NAGIOS_USER}:${NAGIOS_USER} ${NAGIOS_HOME}/etc/htpasswd.users
fi

sed -i -e 's/APACHE_FRONTEND_PORT/'${APACHE_FRONTEND_PORT}'/' /etc/apache2/ports.conf
sed -i -e 's/APACHE_FRONTEND_SECURE_PORT/'${APACHE_FRONTEND_SECURE_PORT}'/' /etc/apache2/ports.conf

/etc/init.d/apache2 restart
/etc/init.d/nagios restart
exec /usr/local/bin/nagios_config_discovery_bot.py -d --prometheus_api $PROMETHEUS_SERVICE --object_file_loc /opt/nagios/etc/objects/prometheus_discovery_objects.cfg
