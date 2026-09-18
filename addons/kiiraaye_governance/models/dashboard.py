from collections import Counter

from dateutil.relativedelta import relativedelta

from odoo import api, fields, models, _
from odoo.exceptions import AccessError


class KiiraayeDashboard(models.Model):
    _name = "kiiraaye.dashboard"
    _description = "Tableau de bord Kiiraaye"
    _rec_name = "name"

    name = fields.Char(
        string="Nom",
        required=True,
        default="Tableau de bord principal",
    )
    code = fields.Char(
        string="Code",
        required=True,
        default="MAIN",
        copy=False,
    )
    active = fields.Boolean(default=True)

    _unique_code = models.Constraint(
        "UNIQUE(code)",
        "Le code du tableau de bord doit être unique.",
    )

    @api.model
    def open_dashboard(self):
        return {
            "type": "ir.actions.client",
            "tag": "kiiraaye_dashboard",
            "name": _("Tableau de bord Kiiraaye"),
        }

    def _check_dashboard_access(self):
        if not self.env.user.has_group("kiiraaye_governance.group_kiiraaye_user"):
            raise AccessError(_("Vous n'avez pas accès au tableau de bord Kiiraaye."))

    @api.model
    def get_dashboard_data(self, filters=None):
        self._check_dashboard_access()
        filters = filters or {}

        Section = self.env["kiiraaye.section"]
        Organisation = self.env["kiiraaye.organisation"]
        Partisan = self.env["kiiraaye.partisan"]
        Geography = self.env["kiiraaye.geographie"]
        Status = self.env["kiiraaye.effectif.status"]

        section_domain = [("active", "=", True)]
        if filters.get("section_id"):
            section_domain.append(("id", "=", int(filters["section_id"])))

        geography_id = filters.get("geographie_id")
        if geography_id:
            geography_id = int(geography_id)
            section_domain += [
                "|",
                "|",
                "|",
                ("region_id", "child_of", geography_id),
                ("departement_id", "child_of", geography_id),
                ("commune_id", "child_of", geography_id),
                ("quartier_id", "child_of", geography_id),
            ]

        sections = Section.search(section_domain)
        open_sections = sections.filtered(lambda s: s.state == "ouverte")
        organizations = Organisation.search(
            [
                ("active", "=", True),
                *(
                    [("id", "=", int(filters["organisation_id"]))]
                    if filters.get("organisation_id")
                    else []
                ),
            ]
        )

        if filters.get("section_id"):
            members = sections.mapped("membre_ids")
        elif filters.get("organisation_id"):
            members = organizations.mapped("member_ids")
        elif geography_id:
            members = sections.mapped("membre_ids")
        else:
            members = Partisan.search([("active", "=", True)])

        members = members.filtered(lambda m: m.active)
        all_members = Partisan.search([])

        status_counter = Counter()
        for section in sections:
            status = Status.get_for_count(section.member_count)
            if status:
                status_counter[status.name] += 1

        org_status_counter = Counter()
        for organisation in organizations:
            status = Status.get_for_count(organisation.member_count)
            if status:
                org_status_counter[status.name] += 1

        section_rows = []
        for section in sorted(
            sections,
            key=lambda s: (-s.member_count, s.name or ""),
        )[:20]:
            section_rows.append(
                {
                    "id": section.id,
                    "name": section.name,
                    "type": dict(section._fields["type_section"].selection).get(
                        section.type_section, section.type_section or ""
                    ),
                    "members": section.member_count,
                    "status": (
                        section.member_status_id.name
                        if section.member_status_id
                        else ""
                    ),
                    "state": dict(section._fields["state"].selection).get(
                        section.state, section.state or ""
                    ),
                }
            )

        organisation_rows = []
        for organisation in sorted(
            organizations,
            key=lambda o: (-o.member_count, o.name or ""),
        )[:20]:
            organisation_rows.append(
                {
                    "id": organisation.id,
                    "name": organisation.name,
                    "type": organisation.type_id.name if organisation.type_id else "",
                    "level": organisation.niveau or 0,
                    "members": organisation.member_count,
                    "status": (
                        organisation.member_status_id.name
                        if organisation.member_status_id
                        else ""
                    ),
                }
            )

        level_labels = {
            "pays": "Pays",
            "niveau1": "Région",
            "niveau2": "Département",
            "niveau3": "Commune / Ville",
            "niveau4": "Niveau local",
            "niveau5": "Quartier",
            "niveau6": "Zone locale",
            "localite": "Localité",
        }
        level_counter = Counter()
        for zone in Geography.search([("active", "=", True)]):
            level_counter[level_labels.get(zone.niveau, zone.niveau)] += 1

        member_state = {
            "actifs": len(members),
            "inactifs": len(all_members.filtered(lambda m: not m.active)),
            "total": len(all_members),
        }

        now = fields.Datetime.now()
        monthly = []
        cursor = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0) - relativedelta(
            months=11
        )
        for index in range(12):
            start = cursor + relativedelta(months=index)
            end = start + relativedelta(months=1)
            count = len(
                members.filtered(
                    lambda m: m.create_date
                    and start <= m.create_date < end
                )
            )
            monthly.append(
                {
                    "label": start.strftime("%m/%Y"),
                    "value": count,
                }
            )

        values = [item["value"] for item in monthly]
        trend = 0.0
        if len(values) >= 2:
            x_mean = (len(values) - 1) / 2.0
            y_mean = sum(values) / len(values)
            numerator = sum(
                (x - x_mean) * (y - y_mean)
                for x, y in enumerate(values)
            )
            denominator = sum(
                (x - x_mean) ** 2 for x in range(len(values))
            )
            if denominator:
                trend = numerator / denominator

        projection = []
        base_total = len(members)
        for step in range(1, 7):
            projected_additions = max(0, round(
                values[-1] + trend * step
            ))
            base_total += projected_additions
            projection.append(
                {
                    "label": (
                        cursor
                        + relativedelta(months=11 + step)
                    ).strftime("%m/%Y"),
                    "value": base_total,
                }
            )

        geography_rows = []
        zones_without_sections = 0
        zones = Geography.search(
            [("active", "=", True)],
            order="niveau, name",
            limit=60,
        )
        for zone in zones:
            zone_sections = Section.search(
                [
                    ("active", "=", True),
                    "|",
                    "|",
                    "|",
                    ("region_id", "child_of", zone.id),
                    ("departement_id", "child_of", zone.id),
                    ("commune_id", "child_of", zone.id),
                    ("quartier_id", "child_of", zone.id),
                ]
            )
            zone_members = zone_sections.mapped("membre_ids").filtered(
                lambda m: m.active
            )
            if not zone_sections:
                zones_without_sections += 1
            geography_rows.append(
                {
                    "id": zone.id,
                    "name": zone.name,
                    "level": level_labels.get(zone.niveau, zone.niveau),
                    "sections": len(zone_sections),
                    "members": len(zone_members),
                }
            )

        geography_rows.sort(
            key=lambda row: (-row["members"], -row["sections"], row["name"])
        )

        return {
            "filters": {
                "sections": [
                    {"id": section.id, "name": section.name}
                    for section in Section.search(
                        [("active", "=", True)],
                        order="name",
                        limit=500,
                    )
                ],
                "organisations": [
                    {"id": organisation.id, "name": organisation.name}
                    for organisation in Organisation.search(
                        [("active", "=", True)],
                        order="name",
                        limit=500,
                    )
                ],
                "geographies": [
                    {
                        "id": zone.id,
                        "name": zone.name,
                        "level": level_labels.get(zone.niveau, zone.niveau),
                    }
                    for zone in Geography.search(
                        [("active", "=", True)],
                        order="niveau, name",
                        limit=1000,
                    )
                ],
            },
            "kpis": {
                "members": len(members),
                "all_members": len(all_members),
                "sections": len(sections),
                "open_sections": len(open_sections),
                "organisations": len(organizations),
                "geographies": Geography.search_count([("active", "=", True)]),
                "zones_without_sections": zones_without_sections,
                "avg_members_per_section": (
                    round(sum(s.member_count for s in sections) / len(sections), 1)
                    if sections
                    else 0
                ),
            },
            "member_state": member_state,
            "section_statuses": [
                {"label": label, "value": value}
                for label, value in sorted(status_counter.items())
            ],
            "organisation_statuses": [
                {"label": label, "value": value}
                for label, value in sorted(org_status_counter.items())
            ],
            "sections": section_rows,
            "organisations": organisation_rows,
            "geography_rows": geography_rows[:25],
            "geography_levels": [
                {"label": label, "value": value}
                for label, value in sorted(level_counter.items())
            ],
            "member_creation": monthly,
            "member_projection": projection,
            "projection_type": "Projection d'effectif à partir de la tendance des créations de membres",
            "historical_election": {
                "available": False,
                "message": _("Aucune donnée d'élection historique n'est actuellement structurée dans le module."),
            },
        }
