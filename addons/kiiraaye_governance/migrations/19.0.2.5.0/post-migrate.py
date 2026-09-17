# -*- coding: utf-8 -*-
import logging

from odoo import SUPERUSER_ID, api

_logger = logging.getLogger(__name__)


def migrate(cr, version):
    if not version or version >= "19.0.2.5.0":
        return

    env = api.Environment(cr, SUPERUSER_ID, {})
    senegal = env["res.country"].search([("code", "=", "SN")], limit=1)
    if not senegal:
        return

    # Garantit la configuration du niveau Quartier même lorsque le pays
    # avait déjà été créé avant l'introduction du niveau 5.
    values = {
        "kiiraaye_geo_quartier_level": "niveau5",
        "kiiraaye_geo_quartier_label": "Quartier / unité locale",
    }
    try:
        senegal.sudo().write(values)
        _logger.info("Configuration du niveau Quartier Sénégal mise à jour.")
    except Exception as exc:
        _logger.warning(
            "Impossible de configurer le niveau Quartier du Sénégal pendant la migration %s: %s",
            "19.0.2.5.0",
            exc,
        )
