# -*- coding: utf-8 -*-
import logging

from odoo import SUPERUSER_ID, api

_logger = logging.getLogger(__name__)


def migrate(cr, version):
    if not version or version >= "19.0.2.6.0":
        return

    env = api.Environment(cr, SUPERUSER_ID, {})
    senegal = env["res.country"].search([("code", "=", "SN")], limit=1)
    if not senegal:
        return

    try:
        senegal.action_load_senegal_default_geography()
        _logger.info(
            "Référentiel Sénégal rechargé : communes et unités locales/quartiers rattachés aux communes."
        )
    except Exception as exc:
        _logger.warning(
            "Impossible de charger les quartiers/unités locales des communes du Sénégal pendant la migration %s: %s",
            "19.0.2.6.0",
            exc,
        )
