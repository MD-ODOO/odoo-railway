FROM odoo:19.0

# Railway uses its own start command when configured. Keep the custom entrypoint
# so the Kiiraaye schema migration runs before any Odoo HTTP request.
ENTRYPOINT ["/usr/local/bin/kiiraaye-entrypoint.sh"]

USER root

RUN python3 -m pip install --break-system-packages --no-cache-dir \
    "qifparse==0.5" \
    "ofxparse==0.21" \
    "openpyxl" \
    "xlsxwriter"

RUN mkdir -p /mnt/extra-addons \
    && chown -R odoo:odoo /mnt/extra-addons

COPY addons/ /mnt/extra-addons/
COPY scripts/kiiraaye-entrypoint.sh /usr/local/bin/kiiraaye-entrypoint.sh

RUN chmod +x /usr/local/bin/kiiraaye-entrypoint.sh \
    && chown -R odoo:odoo /mnt/extra-addons \
    && chown root:root /usr/local/bin/kiiraaye-entrypoint.sh \
    && test -f /mnt/extra-addons/paie_senegal_simulation/views/salary_simulation_views.xml \
    && test -f /mnt/extra-addons/paie_senegal_simulation/__manifest__.py

CMD ["odoo"]
