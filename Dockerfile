FROM odoo:19.0

USER root

RUN mkdir -p /mnt/extra-addons

COPY addons/ /mnt/extra-addons/

RUN chown -R odoo:odoo /mnt/extra-addons

COPY config/odoo.conf /etc/odoo/odoo.conf

USER odoo
