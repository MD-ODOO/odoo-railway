#!/bin/bash
set -euo pipefail

echo "[odoo] running database schema patch and module upgrades" >&2
/usr/local/bin/kiiraaye-upgrade.sh

if [ "$#" -gt 0 ]; then
    exec "$@"
fi

exec su -s /bin/bash odoo -c 'odoo --db_host="${ODOO_DB_HOST:-postgres.railway.internal}" --db_port="${ODOO_DB_PORT:-5432}" --db_user="${ODOO_DB_USER:-odoo}" --db_password="${ODOO_DB_PASSWORD:-}"'
