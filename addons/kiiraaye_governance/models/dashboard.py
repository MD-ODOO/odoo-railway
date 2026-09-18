from collections import defaultdict

from dateutil.relativedelta import relativedelta

from odoo import api, fields, models, _
from odoo.exceptions import AccessError


class KiiraayeDashboard(models.Model):
    _name = "kiiraaye.dashboard"
    _description = "Tableau de bord Kiiraaye"
    _rec_name = "name"

    # Volumétrie cible du moteur de pilotage.
    MAX_SUPPORTED_SECTIONS = 1_000_000
    MAX_SUPPORTED_MEMBERS = 5_000_000
    MAX_BROWSER_SECTION_ROWS = 20
    MAX_BROWSER_ORGANISATION_ROWS = 20
    MAX_BROWSER_GEOGRAPHY_ROWS = 25
    MAX_FILTER_SECTION_ROWS = 1_000

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

    def _auto_init(self):
        result = super()._auto_init()
        # Indexes dédiés aux requêtes de volumétrie du dashboard.
        indexes = (
            (
                "kiiraaye_partisan_create_date_idx",
                "CREATE INDEX IF NOT EXISTS "
                "kiiraaye_partisan_create_date_idx "
                "ON kiiraaye_partisan (create_date)",
            ),
            (
                "kiiraaye_section_partisan_rel_section_idx",
                "CREATE INDEX IF NOT EXISTS "
                "kiiraaye_section_partisan_rel_section_idx "
                "ON kiiraaye_section_partisan_rel (section_id)",
            ),
            (
                "kiiraaye_section_partisan_rel_partisan_idx",
                "CREATE INDEX IF NOT EXISTS "
                "kiiraaye_section_partisan_rel_partisan_idx "
                "ON kiiraaye_section_partisan_rel (partisan_id)",
            ),
            (
                "kiiraaye_organisation_partisan_rel_organisation_idx",
                "CREATE INDEX IF NOT EXISTS "
                "kiiraaye_organisation_partisan_rel_organisation_idx "
                "ON kiiraaye_organisation_partisan_rel (organisation_id)",
            ),
            (
                "kiiraaye_organisation_partisan_rel_partisan_idx",
                "CREATE INDEX IF NOT EXISTS "
                "kiiraaye_organisation_partisan_rel_partisan_idx "
                "ON kiiraaye_organisation_partisan_rel (partisan_id)",
            ),
        )
        for _name, query in indexes:
            self.env.cr.execute(query)
        return result

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

    @staticmethod
    def _selection_label(field, value):
        if not value:
            return ""
        selection = field.selection
        if callable(selection):
            selection = selection()
        return dict(selection).get(value, value)

    def _section_domain(self, filters):
        domain = [("active", "=", True)]
        if filters.get("section_id"):
            domain.append(("id", "=", int(filters["section_id"])))

        geography_id = filters.get("geographie_id")
        if geography_id:
            geography_id = int(geography_id)
            domain += [
                "|",
                "|",
                "|",
                ("region_id", "child_of", geography_id),
                ("departement_id", "child_of", geography_id),
                ("commune_id", "child_of", geography_id),
                ("quartier_id", "child_of", geography_id),
            ]
        return domain

    def _member_domain(self, filters):
        domain = [("active", "=", True)]

        if filters.get("section_id"):
            domain.append(("section_ids", "=", int(filters["section_id"])))
        elif filters.get("organisation_id"):
            domain.append(
                ("organisation_ids", "=", int(filters["organisation_id"]))
            )
        elif filters.get("geographie_id"):
            geography_id = int(filters["geographie_id"])
            domain += [
                "|",
                "|",
                "|",
                ("region_id", "child_of", geography_id),
                ("departement_id", "child_of", geography_id),
                ("commune_id", "child_of", geography_id),
                ("quartier_id", "child_of", geography_id),
            ]
        return domain

    def _organisation_domain(self, filters):
        domain = [("active", "=", True)]
        if filters.get("organisation_id"):
            domain.append(("id", "=", int(filters["organisation_id"])))
        return domain

    def _get_top_section_rows(self, member_domain, Section):
        rows = []
        grouped = self.env["kiiraaye.partisan"]._read_group(
            member_domain,
            ["section_ids"],
            ["__count"],
            limit=self.MAX_BROWSER_SECTION_ROWS,
            order="__count DESC",
        )
        for section, count in grouped:
            if not section:
                continue
            record = section[:1]
            count = int(count or 0)
            status = self.env["kiiraaye.effectif.status"].get_for_count(count)
            rows.append(
                {
                    "id": record.id,
                    "name": record.name,
                    "type": self._selection_label(
                        Section._fields["type_section"],
                        record.type_section,
                    ),
                    "members": count,
                    "status": status.name if status else "",
                    "state": self._selection_label(
                        Section._fields["state"],
                        record.state,
                    ),
                }
            )
        return rows

    def _get_top_organisation_rows(self, member_domain, Organisation):
        rows = []
        grouped = self.env["kiiraaye.partisan"]._read_group(
            member_domain,
            ["organisation_ids"],
            ["__count"],
            limit=self.MAX_BROWSER_ORGANISATION_ROWS,
            order="__count DESC",
        )
        for organisation, count in grouped:
            if not organisation:
                continue
            record = organisation[:1]
            count = int(count or 0)
            status = self.env["kiiraaye.effectif.status"].get_for_count(count)
            rows.append(
                {
                    "id": record.id,
                    "name": record.name,
                    "type": (
                        record.type_id.name
                        if record.type_id
                        else ""
                    ),
                    "level": record.niveau or 0,
                    "members": count,
                    "status": status.name if status else "",
                }
            )
        return rows

    def _get_creation_history(self, member_domain):
        now = fields.Datetime.now()
        first_month = (
            now.replace(
                day=1,
                hour=0,
                minute=0,
                second=0,
                microsecond=0,
            )
            - relativedelta(months=11)
        )
        end_month = first_month + relativedelta(months=12)

        domain = list(member_domain)
        domain += [
            ("create_date", ">=", first_month),
            ("create_date", "<", end_month),
        ]

        grouped = self.env["kiiraaye.partisan"]._read_group(
            domain,
            ["create_date:month"],
            ["__count"],
            order="create_date:month",
        )
        counts = {}
        for bucket, count in grouped:
            if bucket:
                counts[bucket.strftime("%Y-%m")] = int(count or 0)

        result = []
        for index in range(12):
            month = first_month + relativedelta(months=index)
            result.append(
                {
                    "label": month.strftime("%m/%Y"),
                    "value": counts.get(month.strftime("%Y-%m"), 0),
                }
            )
        return result

    def _geography_coverage(self, Geography, Section, Partisan):
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

        level_groups = self.env["kiiraaye.geographie"]._read_group(
            [("active", "=", True)],
            ["niveau"],
            ["__count"],
            order="niveau",
        )
        geography_levels = [
            {
                "label": level_labels.get(level, level),
                "value": int(count or 0),
            }
            for level, count in level_groups
        ]

        zones = Geography.search(
            [("active", "=", True)],
            order="niveau, name",
            limit=self.MAX_BROWSER_GEOGRAPHY_ROWS,
        )

        section_counts = {
            field_name: {
                record.id: int(count or 0)
                for record, count in Section._read_group(
                    [("active", "=", True)],
                    [field_name],
                    ["__count"],
                    order="__count DESC",
                )
                if record
            }
            for field_name in (
                "region_id",
                "departement_id",
                "commune_id",
                "quartier_id",
            )
        }

        member_counts = {
            field_name: {
                record.id: int(count or 0)
                for record, count in Partisan._read_group(
                    [("active", "=", True)],
                    [field_name],
                    ["__count"],
                    order="__count DESC",
                )
                if record
            }
            for field_name in (
                "region_id",
                "departement_id",
                "commune_id",
                "quartier_id",
            )
        }

        field_by_level = {
            "niveau1": "region_id",
            "niveau2": "departement_id",
            "niveau3": "commune_id",
            "niveau5": "quartier_id",
        }

        rows = []
        for zone in zones:
            field_name = field_by_level.get(zone.niveau)
            rows.append(
                {
                    "id": zone.id,
                    "name": zone.name,
                    "level": level_labels.get(zone.niveau, zone.niveau),
                    "sections": (
                        section_counts.get(field_name, {}).get(zone.id, 0)
                        if field_name
                        else 0
                    ),
                    "members": (
                        member_counts.get(field_name, {}).get(zone.id, 0)
                        if field_name
                        else 0
                    ),
                }
            )

        rows.sort(
            key=lambda row: (
                -row["members"],
                -row["sections"],
                row["name"],
            )
        )
        return geography_levels, rows

    @api.model
    def get_dashboard_data(self, filters=None):
        self._check_dashboard_access()
        filters = filters or {}
        current_view = filters.get("view", "global")

        Section = self.env["kiiraaye.section"]
        Organisation = self.env["kiiraaye.organisation"]
        Partisan = self.env["kiiraaye.partisan"]
        Geography = self.env["kiiraaye.geographie"]

        section_domain = self._section_domain(filters)
        member_domain = self._member_domain(filters)
        organisation_domain = self._organisation_domain(filters)

        # IMPORTANT :
        # Ne jamais charger des millions de recordsets dans le navigateur.
        # Les gros volumes sont comptés/agrégés en base et seuls des petits
        # échantillons sont envoyés à OWL.
        section_count = Section.search_count(section_domain)
        open_section_count = Section.search_count(
            section_domain + [("state", "=", "ouverte")]
        )
        organisation_count = Organisation.search_count(organisation_domain)

        current_member_count = Partisan.search_count(member_domain)
        total_member_count = Partisan.search_count([])
        inactive_member_count = Partisan.search_count([("active", "=", False)])

        section_rows = []
        organisation_rows = []
        member_creation = []
        geography_levels = []
        geography_rows = []

        if current_view in ("global", "section"):
            section_rows = self._get_top_section_rows(member_domain, Section)
        if current_view == "global":
            organisation_rows = self._get_top_organisation_rows(
                member_domain,
                Organisation,
            )
        if current_view == "membre":
            member_creation = self._get_creation_history(member_domain)
        if current_view == "lieu":
            geography_levels, geography_rows = self._geography_coverage(
                Geography,
                Section,
                Partisan,
            )

        status_counter = defaultdict(int)
        for row in section_rows:
            if row["status"]:
                status_counter[row["status"]] += 1

        organisation_status_counter = defaultdict(int)
        for row in organisation_rows:
            if row["status"]:
                organisation_status_counter[row["status"]] += 1

        values = [item["value"] for item in member_creation]
        trend = 0.0
        if len(values) >= 2:
            x_mean = (len(values) - 1) / 2.0
            y_mean = sum(values) / len(values)
            numerator = sum(
                (x - x_mean) * (y - y_mean)
                for x, y in enumerate(values)
            )
            denominator = sum(
                (x - x_mean) ** 2
                for x in range(len(values))
            )
            if denominator:
                trend = numerator / denominator

        projection = []
        projected_total = current_member_count
        projection_base = (
            fields.Datetime.now().replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        )
        for step in range(1, 7):
            projected_additions = max(
                0,
                round(values[-1] + trend * step),
            )
            projected_total += projected_additions
            projection.append(
                {
                    "label": (
                        projection_base + relativedelta(months=step)
                    ).strftime("%m/%Y"),
                    "value": projected_total,
                }
            )

        avg_members_per_section = (
            round(current_member_count / section_count, 1)
            if section_count
            else 0
        )

        section_filter_rows = [
            {"id": section.id, "name": section.name}
            for section in Section.search(
                [("active", "=", True)],
                order="name",
                limit=self.MAX_FILTER_SECTION_ROWS,
            )
        ]

        organisation_filter_rows = [
            {"id": organisation.id, "name": organisation.name}
            for organisation in Organisation.search(
                [("active", "=", True)],
                order="name",
                limit=500,
            )
        ]

        geography_filter_rows = [
            {
                "id": zone.id,
                "name": zone.name,
                "level": {
                    "pays": "Pays",
                    "niveau1": "Région",
                    "niveau2": "Département",
                    "niveau3": "Commune / Ville",
                    "niveau4": "Niveau local",
                    "niveau5": "Quartier",
                    "niveau6": "Zone locale",
                    "localite": "Localité",
                }.get(zone.niveau, zone.niveau),
            }
            for zone in Geography.search(
                [("active", "=", True)],
                order="niveau, name",
                limit=1000,
            )
        ]

        return {
            "capacity": {
                "sections_supported": self.MAX_SUPPORTED_SECTIONS,
                "members_supported": self.MAX_SUPPORTED_MEMBERS,
                "browser_section_rows": self.MAX_BROWSER_SECTION_ROWS,
                "browser_organisation_rows": self.MAX_BROWSER_ORGANISATION_ROWS,
                "strategy": "Comptage et agrégation en base, payload OWL limité.",
            },
            "filters": {
                "sections": section_filter_rows,
                "organisations": organisation_filter_rows,
                "geographies": geography_filter_rows,
            },
            "kpis": {
                "members": current_member_count,
                "all_members": total_member_count,
                "sections": section_count,
                "open_sections": open_section_count,
                "organisations": organisation_count,
                "geographies": Geography.search_count(
                    [("active", "=", True)]
                ),
                "zones_without_sections": sum(
                    1 for row in geography_rows if not row["sections"]
                ),
                "avg_members_per_section": avg_members_per_section,
            },
            "member_state": {
                "actifs": (
                    current_member_count
                    if filters.get("section_id")
                    or filters.get("organisation_id")
                    or filters.get("geographie_id")
                    else total_member_count - inactive_member_count
                ),
                "inactifs": inactive_member_count,
                "total": total_member_count,
            },
            "section_statuses": [
                {"label": label, "value": value}
                for label, value in sorted(status_counter.items())
            ],
            "organisation_statuses": [
                {"label": label, "value": value}
                for label, value in sorted(
                    organisation_status_counter.items()
                )
            ],
            "sections": section_rows,
            "organisations": organisation_rows,
            "geography_rows": geography_rows,
            "geography_levels": geography_levels,
            "member_creation": member_creation,
            "member_projection": projection,
            "projection_type": (
                "Projection descriptive de l'évolution des effectifs "
                "à partir de la tendance des créations de membres."
            ),
            "historical_election": {
                "available": False,
                "message": _(
                    "Aucune donnée d'élection historique n'est actuellement "
                    "structurée dans le module."
                ),
            },
        }
