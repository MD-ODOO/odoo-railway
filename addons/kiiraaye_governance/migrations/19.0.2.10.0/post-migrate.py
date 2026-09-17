# -*- coding: utf-8 -*-
import logging

from odoo import SUPERUSER_ID, api

_logger = logging.getLogger(__name__)


def migrate(cr, version):
    if not version or version >= "19.0.2.10.0":
        return

    env = api.Environment(cr, SUPERUSER_ID, {})
    Member = env["kiiraaye.partisan"].sudo()
    sequence = env.ref(
        "kiiraaye_governance.seq_kiiraaye_partisan",
        raise_if_not_found=False,
    )
    if not sequence:
        _logger.warning(
            "Séquence des membres Kiiraaye introuvable pendant la migration 19.0.2.10.0."
        )
        return

    members = Member.search([("reference", "in", [False, "", "Nouveau"])])
    count = 0
    for member in members:
        reference = sequence.next_by_code("kiiraaye.partisan")
        if not reference:
            continue
        member.with_context(skip_kiiraaye_reference_check=True).write(
            {"reference": reference}
        )
        count += 1

    _logger.info(
        "Migration 19.0.2.10.0 : %s membre(s) sans référence réelle ont reçu un numéro membre.",
        count,
    )
