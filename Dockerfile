FROM odoo:19.0

# Disable the official Odoo image entrypoint so Railway Start Command is executed directly.
ENTRYPOINT []

USER root

# Python dependencies required by base_accounting_kit.
# Keep them in the image so Odoo's external_dependencies check succeeds.
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

CMD ["sh", "-c", "chown -R odoo:odoo /var/lib/odoo && exec su -s /bin/bash odoo -c 'odoo --db_host=\"${ODOO_DB_HOST:-postgres.railway.internal}\" --db_port=\"${ODOO_DB_PORT:-5432}\" --db_user=\"${ODOO_DB_USER:-odoo}\" --db_password=\"${ODOO_DB_PASSWORD:-}\"'"]
