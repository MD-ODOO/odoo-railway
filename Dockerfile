FROM odoo:19.0

# Disable the official Odoo image entrypoint so Railway Start Command is executed directly.
ENTRYPOINT []

USER root

# Python dependencies required by base_accounting_kit.
# Keep them in the image so Odoo external dependency checks succeed.
RUN python3 -m pip install --break-system-packages --no-cache-dir \
    "qifparse==0.5" \
    "ofxparse==0.21" \
    "openpyxl" \
    "xlsxwriter"

RUN mkdir -p /mnt/extra-addons \
    && chown -R odoo:odoo /mnt/extra-addons

COPY addons/ /mnt/extra-addons/

RUN chown -R odoo:odoo /mnt/extra-addons \
    && test -f /mnt/extra-addons/paie_senegal_simulation/views/salary_simulation_views.xml \
    && test -f /mnt/extra-addons/paie_senegal_simulation/__manifest__.py

# Odoo 19: -u requires -d. Each database must be upgraded separately.
# A comma-separated -d list does not upgrade every database; it restricts access
# and the documented example updates only the selected database.
CMD ["sh", "-c", "DB_HOST=\"${ODOO_DB_HOST:-postgres.railway.internal}\"; DB_PORT=\"${ODOO_DB_PORT:-5432}\"; DB_USER=\"${ODOO_DB_USER:-odoo}\"; DB_PASSWORD=\"${ODOO_DB_PASSWORD:-}\"; UPDATE_DBS=\"${ODOO_UPDATE_DATABASES:-KIIRAAY,SMART}\"; chown -R odoo:odoo /var/lib/odoo; exec su -s /bin/bash odoo -c \"for DB_NAME in \\$(printf \\\"%s\\" \\\"$UPDATE_DBS\\" | tr \\",\\" \\\" \\"); do echo \\\"[kiiraaye] upgrading $DB_NAME\\"; odoo -d \\\"$DB_NAME\\" -u kiiraaye_governance --stop-after-init --db_host=\\\"$DB_HOST\\\" --db_port=\\\"$DB_PORT\\\" --db_user=\\\"$DB_USER\\\" --db_password=\\\"$DB_PASSWORD\\\" || exit \\\"$?\\"; done; exec odoo --db_host=\\\"$DB_HOST\\\" --db_port=\\\"$DB_PORT\\\" --db_user=\\\"$DB_USER\\\" --db_password=\\\"$DB_PASSWORD\\\"\""]