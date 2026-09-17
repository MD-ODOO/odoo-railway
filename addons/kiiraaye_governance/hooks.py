from odoo import api


def post_init_hook(env):
    """Create one Kiiraaye geographic root for every country already provided by Odoo."""
    countries = env["res.country"].sudo().search([])
    Geo = env["kiiraaye.geographie"].sudo()

    existing_country_ids = set(
        Geo.search([("niveau", "=", "pays")]).mapped("country_id").ids
    )

    vals_list = [
        {
            "name": country.name,
            "code": country.code,
            "country_id": country.id,
            "niveau": "pays",
            "source": "Odoo / res.country",
        }
        for country in countries
        if country.id not in existing_country_ids
    ]
    if vals_list:
        Geo.create(vals_list)
