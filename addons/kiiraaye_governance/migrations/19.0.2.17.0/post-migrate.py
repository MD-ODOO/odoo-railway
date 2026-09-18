# -*- coding: utf-8 -*-
import logging

from odoo import SUPERUSER_ID, api, Command

_logger = logging.getLogger(__name__)


def migrate(cr, version):
    if not version or version >= "19.0.2.17.0":
        return

    env = api.Environment(cr, SUPERUSER_ID, {})

    OrganisationType = env["kiiraaye.organisation.type"].sudo()
    Organisation = env["kiiraaye.organisation"].sudo()
    Cadre = env["kiiraaye.cadre"].sudo()
    Partisan = env["kiiraaye.partisan"].sudo()

    cadre_type = OrganisationType.search([("code", "=", "CADRE")], limit=1)
    if not cadre_type:
        cadre_type = OrganisationType.create(
            {
                "name": "Cadre",
                "code": "CADRE",
                "niveau": 1,
                "sequence": 10,
                "active": True,
            }
        )

    migrated = 0
    for cadre in Cadre.search([]):
        organisation = Organisation.search(
            [("legacy_cadre_id", "=", cadre.id)],
            limit=1,
        )
        if not organisation:
            organisation = Organisation.search(
                [("code", "=", "CADRE-%s" % cadre.code)],
                limit=1,
            )

        values = {
            "name": cadre.name,
            "code": "CADRE-%s" % cadre.code,
            "type_id": cadre_type.id,
            "sequence": cadre.sequence,
            "color": cadre.color,
            "description": cadre.description,
            "active": cadre.active,
            "legacy_cadre_id": cadre.id,
        }

        if organisation:
            organisation.write(values)
        else:
            organisation = Organisation.create(values)

        for member in cadre.member_ids:
            if member not in organisation.member_ids:
                member.write(
                    {"organisation_ids": [Command.link(organisation.id)]}
                )
        migrated += 1

    # Les membres qui possèdent encore un ancien cadre mais n'ont pas été
    # parcourus par la boucle sont également synchronisés.
    for member in Partisan.search([("cadre_id", "!=", False)]):
        organisation = Organisation.search(
            [("legacy_cadre_id", "=", member.cadre_id.id)],
            limit=1,
        )
        if organisation and member not in organisation.member_ids:
            member.write(
                {"organisation_ids": [Command.link(organisation.id)]}
            )

    _logger.info(
        "Migration 19.0.2.17.0 : %s ancien(s) cadre(s) converti(s) en organisation(s) KIIRAAYE.",
        migrated,
    )
