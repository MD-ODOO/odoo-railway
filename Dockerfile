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

# SA Property Management — free/open-source LGPL-3 Odoo 18/19 module.
# Pin the source commit for reproducible Railway builds.
RUN set -eux; \
    git clone --depth 1 https://github.com/otomatercom-cloud/sa_property_management.git /tmp/sa_property_management; \
    cd /tmp/sa_property_management; \
    git fetch --depth 1 origin b25ad74c137d748b09e14c5bdd2c8b8186273412; \
    git checkout b25ad74c137d748b09e14c5bdd2c8b8186273412; \
    rm -rf __pycache__ */__pycache__; \
    cp -a . /mnt/extra-addons/sa_property_management/; \
    rm -rf /mnt/extra-addons/sa_property_management/.git /tmp/sa_property_management; \
    chown -R odoo:odoo /mnt/extra-addons/sa_property_management

COPY scripts/kiiraaye-upgrade.sh /usr/local/bin/kiiraaye-upgrade.sh
COPY scripts/start-odoo.sh /usr/local/bin/start-odoo.sh
COPY scripts/kiiraaye_schema_patch.py /usr/local/bin/kiiraaye_schema_patch.py
COPY scripts/cleanup_kiiraaye_dakar.py /usr/local/bin/cleanup_kiiraaye_dakar.py

RUN chmod +x /usr/local/bin/kiiraaye-upgrade.sh /usr/local/bin/start-odoo.sh /usr/local/bin/kiiraaye_schema_patch.py \
    && chown -R odoo:odoo /mnt/extra-addons \
    && chown root:root /usr/local/bin/kiiraaye-upgrade.sh /usr/local/bin/start-odoo.sh /usr/local/bin/kiiraaye_schema_patch.py /usr/local/bin/cleanup_kiiraaye_dakar.py \
    && test -f /mnt/extra-addons/paie_senegal_simulation/views/salary_simulation_views.xml \
    && test -f /mnt/extra-addons/paie_senegal_simulation/__manifest__.py \
    && test -f /mnt/extra-addons/sa_property_management/__manifest__.py \
    && test -f /mnt/extra-addons/sa_property_management/i18n/fr.po

ENTRYPOINT ["/usr/local/bin/start-odoo.sh"]
CMD ["odoo"]
