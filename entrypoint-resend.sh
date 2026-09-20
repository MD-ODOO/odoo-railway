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
    # Force the Railway PostgreSQL connection. The official Odoo image
    # ships with db_host/db_port/db_user/db_password entries in odoo.conf,
    # so the standard entrypoint may otherwise keep using the local socket.
    "db_host": os.getenv("HOST", ""),
    "db_port": os.getenv("PORT", "5432"),
    "db_user": os.getenv("USER", ""),
    "db_password": os.getenv("PASSWORD", ""),
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
exec /entrypoint.sh "$@"
