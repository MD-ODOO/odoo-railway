#!/bin/bash
set -euo pipefail

# Odoo runtime configuration for Railway.
# Database and SMTP secrets are read only from the runtime environment
# and are never stored in Git.

RESEND_PASSWORD="${RESEND_SMTP_PASSWORD:-${RESEND_API_KEY:-}}"

BASE_CONFIG="${ODOO_RC:-/etc/odoo/odoo.conf}"
RUNTIME_CONFIG="/tmp/odoo-railway.conf"

cp "${BASE_CONFIG}" "${RUNTIME_CONFIG}"

python3 - "${RUNTIME_CONFIG}" <<'PY'
import os
import re
import sys

path = sys.argv[1]

values = {
    # Dedicated Odoo database variables. These are intentionally separate
    # from Railway's generic HOST/USER/PASSWORD variables.
    "db_host": os.getenv("ODOO_DB_HOST", "postgres.railway.internal"),
    "db_port": os.getenv("ODOO_DB_PORT", "5432"),
    "db_user": os.getenv("ODOO_DB_USER", "odoo"),
    "db_password": os.getenv("ODOO_DB_PASSWORD", ""),
}

values.update({
    "smtp_server": os.getenv("RESEND_SMTP_HOST", "smtp.resend.com"),
    "smtp_port": os.getenv("RESEND_SMTP_PORT", "465"),
    "smtp_user": os.getenv("RESEND_SMTP_USER", "resend"),
    "smtp_password": os.getenv("RESEND_SMTP_PASSWORD") or os.getenv("RESEND_API_KEY", ""),
    "smtp_ssl": os.getenv("RESEND_SMTP_SSL", "true"),
})

from_email = os.getenv("RESEND_FROM_EMAIL")
if from_email:
    values["email_from"] = from_email

from_filter = os.getenv("RESEND_FROM_FILTER")
if from_filter:
    values["from_filter"] = from_filter

with open(path, "r", encoding="utf-8") as handle:
    lines = handle.readlines()

for key, value in values.items():
    escaped = value.replace("\\", "\\\\")
    pattern = re.compile(r"^\s*#?\s*" + re.escape(key) + r"\s*=.*$")
    replacement = f"{key} = {escaped}\n"

    for index, line in enumerate(lines):
        if pattern.match(line):
            lines[index] = replacement
            break
    else:
        lines.append(replacement)

with open(path, "w", encoding="utf-8") as handle:
    handle.writelines(lines)

os.chmod(path, 0o600)
PY

export RESEND_PASSWORD
export ODOO_RC="${RUNTIME_CONFIG}"
# Do not invoke the official entrypoint here: Railway exposes generic
# HOST/PORT/USER/PASSWORD variables which can make it inject the
# PostgreSQL user "postgres" and override our Odoo config.
exec odoo -c "${RUNTIME_CONFIG}" \
    --db_host="${ODOO_DB_HOST:-postgres.railway.internal}" \
    --db_port="${ODOO_DB_PORT:-5432}" \
    --db_user="${ODOO_DB_USER:-odoo}" \
    --db_password="${ODOO_DB_PASSWORD:-}" \
    "$@"
