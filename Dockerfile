FROM odoo:19.0

USER root

RUN mkdir -p /mnt/extra-addons \
    && chown -R odoo:odoo /mnt/extra-addons

COPY addons/ /mnt/extra-addons/

RUN chown -R odoo:odoo /mnt/extra-addons

USER odoo

USER root
COPY entrypoint-resend.sh /usr/local/bin/entrypoint-resend.sh
RUN chmod 755 /usr/local/bin/entrypoint-resend.sh
USER odoo

ENTRYPOINT ["/usr/local/bin/entrypoint-resend.sh"]
CMD ["odoo"]
