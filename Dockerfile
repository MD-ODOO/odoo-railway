FROM odoo:19.0

ENTRYPOINT []

USER root

RUN python3 -m pip install --break-system-packages --no-cache-dir \
    "qifparse==0.5" \
    "ofxparse==0.21" \
    "openpyxl" \
    "xlsxwriter"

RUN mkdir -p /mnt/extra-addons /usr/local/bin \
    && chown -R odoo:odoo /mnt/extra-addons

COPY addons/ /mnt/extra-addons/
COPY scripts/kiiraaye-upgrade.sh /usr/local/bin/kiiraaye-upgrade.sh
COPY scripts/cleanup_kiiraaye_dakar.py /usr/local/bin/cleanup_kiiraaye_dakar.py

RUN chmod +x /usr/local/bin/kiiraaye-upgrade.sh \
    && chown -R odoo:odoo /mnt/extra-addons \
    && chown root:root /usr/local/bin/kiiraaye-upgrade.sh /usr/local/bin/cleanup_kiiraaye_dakar.py \
    && test -f /mnt/extra-addons/paie_senegal_simulation/views/salary_simulation_views.xml \
    && test -f /mnt/extra-addons/paie_senegal_simulation/__manifest__.py

CMD ["/bin/bash", "-c", "/usr/local/bin/kiiraaye-upgrade.sh && exec odoo"]