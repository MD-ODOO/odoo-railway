#!/bin/bash
set -euo pipefail

echo "[odoo] preparing database schema and upgrading Immobilier SN" >&2
/usr/local/bin/kiiraaye-upgrade.sh

# Always start the web server after the preparation step; never re-execute this script
# from arguments supplied by a platform start-command override.
exec su -s /bin/bash odoo -c 'odoo --db_host="${ODOO_DB_HOST:-postgres.railway.internal}" --db_port="${ODOO_DB_PORT:-5432}" --db_user="${ODOO_DB_USER:-odoo}" --db_password="${ODOO_DB_PASSWORD:-}"'
