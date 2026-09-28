# -*- coding: utf-8 -*-

from odoo import api, SUPERUSER_ID


def normalize(value):
    return " ".join(str(value or "").strip().casefold().split())


env = api.Environment(cr, SUPERUSER_ID, {})
Geo = env["kiiraaye.geographie"]
Section = env["kiiraaye.section"]

groups = {}
for record in Geo.search([("country_id.code", "=", "SN"), ("name", "=", "Dakar")]):
    key = (record.country_id.id, normalize(record.name), record.niveau)
    groups.setdefault(key, []).append(record)

section_fields = ("region_id", "departement_id", "commune_id", "quartier_id")
deleted = []

for key, records in groups.items():
    if len(records) < 2:
        continue

    scored = []
    for record in records:
        children = Geo.search_count([("parent_id", "=", record.id)])
        section_count = sum(
            Section.search_count([(field_name, "=", record.id)])
            for field_name in section_fields
        )
        score = children * 100000 + section_count
        scored.append((score, record.id, record, children, section_count))

    # Conserver le Dakar qui porte les données/hierarchie.
    scored.sort(key=lambda item: (-item[0], item[1]))
    keeper = scored[0]

    for score, record_id, record, children, section_count in scored[1:]:
        if children == 0 and section_count == 0:
            deleted.append({
                "id": record.id,
                "name": record.name,
                "niveau": record.niveau,
                "keeper_id": keeper[2].id,
            })
            record.unlink()

env.cr.commit()

print("[kiiraaye] nettoyage Dakar:", deleted)
