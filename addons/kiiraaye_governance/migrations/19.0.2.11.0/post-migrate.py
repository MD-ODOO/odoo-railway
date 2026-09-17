# -*- coding: utf-8 -*-
import logging
from odoo import SUPERUSER_ID, api

_logger = logging.getLogger(__name__)


def migrate(cr, version):
    if not version or version >= "19.0.2.11.0":
        return

    env = api.Environment(cr, SUPERUSER_ID, {})
    sequence = env.ref("kiiraaye_governance.seq_kiiraaye_partisan", raise_if_not_found=False)
    if sequence:
        members = env["kiiraaye.partisan"].search([("reference", "in", [False, "", "Nouveau"])])
        for member in members:
            reference = sequence.next_by_code("kiiraaye.partisan")
            if reference:
                member.write({"reference": reference})
        _logger.info("Migration 19.0.2.11.0: member references checked.")

    sync = getattr(env["kiiraaye.section"].sudo(), "_sync_coordinator_access", None)
    if sync:
        sync()
        _logger.info("Migration 19.0.2.11.0: coordinator access synchronized.")
