#!/bin/bash
set -euo pipefail

# Resend SMTP configuration for Odoo.
# Secrets are read only from the runtime environment and never stored in Git.

RESEND_PASSWORD="${RESEND_SMTP_PASSWORD:-${RESEND_API_KEY:-}}"

if [ -z "${RESEND_PASSWORD}" ]; then
    exec /entrypoint.sh "$@"
fi

BASE_CONFIG="${ODOO_RC:-/etc/odoo/odoo.conf}"
RUNTIME_CONFIG="/tmp/odoo-resend.conf"

cp "${BASE_CONFIG}" "${RUNTIME_CONFIG}"

python3 - "${RUNTIME_CONFIG}" <<'PY'
import os
import re
import sys

path = sys.argv[1]

values = {
    "smtp_server": os.getenv("RESEND_SMTP_HOST", "smtp.resend.com"),
    "smtp_port": os.getenv("RESEND_SMTP_PORT", "465"),
    "smtp_user": os.getenv("RESEND_SMTP_USER", "resend"),
    "smtp_password": os.getenv("RESEND_SMTP_PASSWORD") or os.getenv("RESEND_API_KEY", ""),
    "smtp_ssl": os.getenv("RESEND_SMTP_SSL", "true"),
}

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

export ODOO_RC="${RUNTIME_CONFIG}"
exec /entrypoint.sh "$@"
