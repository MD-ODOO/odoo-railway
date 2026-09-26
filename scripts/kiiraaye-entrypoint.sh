#!/bin/bash
set -e

DBS="${ODOO_UPDATE_DATABASES:-KIIRAAY,SMART}"
DB_HOST="${ODOO_DB_HOST:-postgres.railway.internal}"
DB_PORT="${ODOO_DB_PORT:-5432}"
DB_USER="${ODOO_DB_USER:-odoo}"
DB_PASSWORD="${ODOO_DB_PASSWORD:-}"

echo "[kiiraaye] forcing module upgrade on: ${DBS}"

su -s /bin/bash odoo -c "odoo -d \"$DBS\" -u kiiraaye_governance --stop-after-init --db_host=\"$DB_HOST\" --db_port=\"$DB_PORT\" --db_user=\"$DB_USER\" --db_password=\"$DB_PASSWORD\""

echo "[kiiraaye] upgrade finished; starting Odoo"

if [ "$#" -eq 0 ]; then
    set -- odoo
fi

if [ "$1" = "odoo" ] || [ "$1" = "odoo-bin" ]; then
    shift
    exec su -s /bin/bash odoo -c "odoo --db_host=\"$DB_HOST\" --db_port=\"$DB_PORT\" --db_user=\"$DB_USER\" --db_password=\"$DB_PASSWORD\" $*"
fi

exec "$@"
