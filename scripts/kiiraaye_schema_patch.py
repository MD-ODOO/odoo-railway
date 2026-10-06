#!/usr/bin/env python3
import os
import shlex
import subprocess
import psycopg2


DBS = [db.strip() for db in os.getenv("ODOO_UPDATE_DATABASES", "KIIRAAY,SMART").split(",") if db.strip()]
HOST = os.getenv("ODOO_DB_HOST", "postgres.railway.internal")
PORT = int(os.getenv("ODOO_DB_PORT", "5432"))
USER = os.getenv("ODOO_DB_USER", "odoo")
PASSWORD = os.getenv("ODOO_DB_PASSWORD", "")


def patch_schema(dbname):
    print(f"[kiiraaye] schema patch: {dbname}", flush=True)
    conn = psycopg2.connect(
        host=HOST,
        port=PORT,
        user=USER,
        password=PASSWORD,
        dbname=dbname,
    )
    conn.autocommit = True
    try:
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

            cr.execute(
                "SELECT to_regclass('kiiraaye_zone_quartier_rel')"
            )
            relation_exists = cr.fetchone()[0] is not None
            if relation_exists:
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

            cr.execute(
                """
                SELECT count(*)
                  FROM information_schema.columns
                 WHERE table_name = 'res_users'
                   AND column_name = 'kiiraaye_zone_id'
                """
            )
            users_ok = cr.fetchone()[0] == 1
            cr.execute(
                """
                SELECT count(*)
                  FROM information_schema.columns
                 WHERE table_name = 'kiiraaye_geographie'
                   AND column_name = 'zone_id'
                """
            )
            geo_ok = cr.fetchone()[0] == 1
            if not (users_ok and geo_ok):
                raise RuntimeError(
                    f"schema incomplet après patch: res_users={users_ok}, geographie={geo_ok}"
                )
    finally:
        conn.close()


def upgrade(dbname):
    patch_schema(dbname)
    command = (
        "odoo --database %s --update kiiraaye_governance --stop-after-init "
        "--db_host=%s --db_port=%s --db_user=%s --db_password=%s"
        % tuple(
            shlex.quote(str(value))
            for value in (dbname, HOST, PORT, USER, PASSWORD)
        )
    )
    print(f"[kiiraaye] module upgrade (kiiraaye_governance): {dbname}", flush=True)

    result = subprocess.run(
        ["su", "-s", "/bin/bash", "odoo", "-c", command],
        text=True,
    )
    if result.returncode:
        raise SystemExit(result.returncode)


for db in DBS:
    upgrade(db)

print("[kiiraaye] schema patch and module upgrade finished", flush=True)
