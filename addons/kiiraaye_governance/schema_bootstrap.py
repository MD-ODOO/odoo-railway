# -*- coding: utf-8 -*-
"""Small bootstrap for schema columns required before the ORM can read new Kiiraaye fields."""
import logging
import os

import psycopg2

_logger = logging.getLogger(__name__)


def ensure_columns():
    databases = [
        db.strip()
        for db in os.getenv("ODOO_UPDATE_DATABASES", "KIIRAAY,SMART").split(",")
        if db.strip()
    ]
    host = os.getenv("ODOO_DB_HOST", "postgres.railway.internal")
    port = int(os.getenv("ODOO_DB_PORT", "5432"))
    user = os.getenv("ODOO_DB_USER", "odoo")
    password = os.getenv("ODOO_DB_PASSWORD", "")

    for dbname in databases:
        try:
            conn = psycopg2.connect(
                host=host,
                port=port,
                user=user,
                password=password,
                dbname=dbname,
                connect_timeout=10,
            )
            conn.autocommit = True
            with conn.cursor() as cr:
                cr.execute(
                    "ALTER TABLE res_users "
                    "ADD COLUMN IF NOT EXISTS kiiraaye_zone_id integer"
                )
                cr.execute(
                    "CREATE INDEX IF NOT EXISTS res_users_kiiraaye_zone_id_idx "
                    "ON res_users (kiiraaye_zone_id)"
                )
                cr.execute(
                    "ALTER TABLE kiiraaye_geographie "
                    "ADD COLUMN IF NOT EXISTS zone_id integer"
                )
                cr.execute(
                    "CREATE INDEX IF NOT EXISTS kiiraaye_geographie_zone_id_idx "
                    "ON kiiraaye_geographie (zone_id)"
                )
                if _table_exists(cr, "kiiraaye_zone_quartier_rel"):
                    cr.execute(
                        """
                        UPDATE kiiraaye_geographie AS g
                           SET zone_id = rel.zone_id
                          FROM kiiraaye_zone_quartier_rel AS rel
                         WHERE g.id = rel.quartier_id
                           AND g.zone_id IS NULL
                           AND g.niveau = 'niveau5'
                        """
                    )
            conn.close()
            _logger.info("[kiiraaye] schema bootstrap completed for %s", dbname)
        except Exception:
            _logger.exception(
                "[kiiraaye] schema bootstrap failed for %s", dbname
            )


def _table_exists(cr, table_name):
    cr.execute("SELECT to_regclass(%s)", (table_name,))
    return cr.fetchone()[0] is not None


ensure_columns()
