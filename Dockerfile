FROM odoo:19.0

USER root

RUN mkdir -p /mnt/extra-addons \
    && chown -R odoo:odoo /mnt/extra-addons

COPY addons/ /mnt/extra-addons/

RUN chown -R odoo:odoo /mnt/extra-addons

CMD ["sh", "-c", "chown -R odoo:odoo /var/lib/odoo && exec su -s /bin/bash odoo -c 'odoo --db_host=\"\${ODOO_DB_HOST:-postgres.railway.internal}\" --db_port=\"\${ODOO_DB_PORT:-5432}\" --db_user=\"\${ODOO_DB_USER:-odoo}\" --db_password=\"\${ODOO_DB_PASSWORD:-}\"'"]
