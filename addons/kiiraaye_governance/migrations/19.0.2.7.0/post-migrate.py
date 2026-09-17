# -*- coding: utf-8 -*-
import logging

from odoo import SUPERUSER_ID, api

_logger = logging.getLogger(__name__)


def migrate(cr, version):
    if not version or version >= "19.0.2.7.0":
        return

    env = api.Environment(cr, SUPERUSER_ID, {})
    senegal = env["res.country"].search([("code", "=", "SN")], limit=1)
    if not senegal:
        return

    try:
        senegal.action_load_senegal_quartiers()
        _logger.info(
            "Référentiel Sénégal : quartiers/unités locales ANSD rechargés sous les communes existantes."
        )
    except Exception as exc:
        _logger.exception(
            "Échec du chargement automatique des quartiers/unités locales du Sénégal pendant la migration 19.0.2.7.0: %s",
            exc,
        )
