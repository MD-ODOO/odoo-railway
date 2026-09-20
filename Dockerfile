FROM odoo:19.0

USER root

RUN mkdir -p /mnt/extra-addons \
    && chown -R odoo:odoo /mnt/extra-addons

COPY addons/ /mnt/extra-addons/

RUN chown -R odoo:odoo /mnt/extra-addons

CMD ["sh", "-c", "chown -R odoo:odoo /var/lib/odoo && exec su -s /bin/bash odoo -c 'odoo --admin-passwd=\"$ODOO_ADMIN_PASSWORD\" --db_host=\"$ODOO_DB_HOST\" --db_port=\"$ODOO_DB_PORT\" --db_user=\"$ODOO_DB_USER\" --db_password=\"$ODOO_DB_PASSWORD\"'"]
