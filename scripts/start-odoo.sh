#!/bin/bash
set -euo pipefail

echo "[kiiraaye] running database upgrade before Odoo startup"
/usr/local/bin/kiiraaye-upgrade.sh

if [ "$#" -gt 0 ]; then
    exec "$@"
fi

exec odoo
