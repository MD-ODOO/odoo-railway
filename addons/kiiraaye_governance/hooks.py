from odoo import SUPERUSER_ID, api


def _column_exists(cr, table, column):
    cr.execute("SELECT 1 FROM information_schema.columns WHERE table_name=%s AND column_name=%s", (table, column))
    return bool(cr.fetchone())


def _add_user_columns(env):
    cr = env.cr
    if not _column_exists(cr, "res_users", "kiiraaye_geographie_id"):
        cr.execute("ALTER TABLE res_users ADD COLUMN kiiraaye_geographie_id integer")
    if not _column_exists(cr, "res_users", "kiiraaye_poste_id"):
        cr.execute("ALTER TABLE res_users ADD COLUMN kiiraaye_poste_id integer")


def pre_init_hook(env):
    _add_user_columns(env)


def post_init_hook(env):
    Geo = env["kiiraaye.geographie"].sudo()
    countries = env["res.country"].sudo().search([])
    for country in countries:
        exists = Geo.search([
            ("niveau", "=", "pays"),
            ("country_id", "=", country.id),
            ("parent_id", "=", False),
        ], limit=1)
        if not exists:
            Geo.create({
                "name": country.name,
                "code": "COUNTRY-%s" % (country.code or country.id),
                "niveau": "pays",
                "admin_level": 0,
                "country_id": country.id,
                "source_name": "Odoo res.country",
            })
