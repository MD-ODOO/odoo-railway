# -*- coding: utf-8 -*-
import logging
from odoo import SUPERUSER_ID, api

_logger = logging.getLogger(__name__)


def migrate(cr, version):
    if not version or version >= "19.0.2.12.0":
        return

    env = api.Environment(cr, SUPERUSER_ID, {})
    section_model = env["kiiraaye.section"].sudo()
    sync = getattr(section_model, "_sync_coordinator_access", None)
    if sync:
        sync()
        _logger.info(
            "Migration 19.0.2.12.0: synchronisation du groupe Coordonnateur avec les champs de groupes Odoo 19."
        )
