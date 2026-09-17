import logging

from odoo import api

_logger = logging.getLogger(__name__)


def post_init_hook(env):
    """Create country roots and preload the Senegal geographic reference."""
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
            "source_uid": f"COUNTRY-{country.id}",
            "source_admin_level": "MANUAL",
        }
        for country in countries
        if country.id not in existing_country_ids
    ]
    if vals_list:
        Geo.create(vals_list)

    senegal = countries.filtered(lambda country: country.code == "SN")[:1]
    if senegal:
        try:
            senegal.action_load_senegal_default_geography()
        except Exception as exc:
            _logger.warning(
                "Impossible de précharger automatiquement la géographie du Sénégal: %s",
                exc,
            )
