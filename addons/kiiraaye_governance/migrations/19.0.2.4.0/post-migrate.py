# -*- coding: utf-8 -*-
import logging

from odoo import SUPERUSER_ID, api

_logger = logging.getLogger(__name__)


def migrate(cr, version):
    if not version or version >= "19.0.2.4.0":
        return

    env = api.Environment(cr, SUPERUSER_ID, {})
    senegal = env["res.country"].search([("code", "=", "SN")], limit=1)
    if not senegal:
        return

    try:
        senegal.action_load_senegal_default_geography()
    except Exception as exc:
        _logger.warning(
            "Préchargement des unités locales/quartiers du Sénégal impossible pendant la migration %s: %s",
            "19.0.2.4.0",
            exc,
        )
