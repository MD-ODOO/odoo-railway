from collections import defaultdict
import unicodedata

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

    OFFICIAL_SENEGAL_TOTALS = {
        "regions": 14,
        "departments": 46,
        "communes": 557,
    }

    NATIONAL_SECTION_TYPES = (
        "communale",
        "departementale",
        "regionale",
        "nationale",
    )

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

    def _section_scope_domain(self, scope, filters=None):
        filters = filters or {}
        country = self.env["res.country"].search([("code", "=", "SN")], limit=1)

        if scope == "diaspora":
            domain = [
                ("active", "=", True),
                ("type_section", "=", "diaspora"),
            ]
            if country:
                domain.append(("country_id", "!=", country.id))
        else:
            domain = [
                ("active", "=", True),
                ("type_section", "in", self.NATIONAL_SECTION_TYPES),
            ]
            if country:
                domain.append(("country_id", "=", country.id))

        if filters.get("section_id"):
            domain.append(("id", "=", int(filters["section_id"])))

        geography_id = filters.get("geographie_id")
        if geography_id and scope == "national":
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

    def _member_scope_domain(self, scope, filters=None):
        filters = filters or {}
        country = self.env["res.country"].search([("code", "=", "SN")], limit=1)
        domain = [("active", "=", True)]

        if scope == "diaspora":
            domain.append(("section_ids.type_section", "=", "diaspora"))
            if country:
                domain.append(("section_ids.country_id", "!=", country.id))
        else:
            domain.append((
                "section_ids.type_section",
                "in",
                self.NATIONAL_SECTION_TYPES,
            ))
            if country:
                domain.append(("section_ids.country_id", "=", country.id))

        if filters.get("section_id"):
            domain.append(("section_ids", "=", int(filters["section_id"])))
        if filters.get("organisation_id"):
            domain.append(("organisation_ids", "=", int(filters["organisation_id"])))

        geography_id = filters.get("geographie_id")
        if geography_id and scope == "national":
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

    def _effectif_overview(self):
        Partisan = self.env["kiiraaye.partisan"]
        national_count = Partisan.search_count(self._member_scope_domain("national"))
        diaspora_count = Partisan.search_count(self._member_scope_domain("diaspora"))

        total_domain = [
            ("active", "=", True),
            "|",
            "&",
            ("section_ids.type_section", "in", self.NATIONAL_SECTION_TYPES),
            ("section_ids.country_id.code", "=", "SN"),
            "&",
            ("section_ids.type_section", "=", "diaspora"),
            ("section_ids.country_id.code", "!=", "SN"),
        ]
        total_count = Partisan.search_count(total_domain)

        return {
            "national": int(national_count or 0),
            "diaspora": int(diaspora_count or 0),
            "total": int(total_count or 0),
        }

    def _organisation_domain(self, filters):
        domain = [("active", "=", True)]
        if filters.get("organisation_id"):
            domain.append(("id", "=", int(filters["organisation_id"])))
        return domain

    def _get_top_section_rows(self, section_domain, member_domain, Section):
        """Retourne quelques sections sans grouper directement sur un Many2many.

        Odoo 19 utilise un agrégateur SQL pour _read_group et le regroupement
        direct sur section_ids (Many2many) n'est pas une base suffisamment
        portable pour ce tableau de bord. On garde donc le payload limité et
        faisons les comptages par section, ce qui reste borné à 20 requêtes.
        """
        rows = []
        # Le domaine géographique/section limite l'échantillon ; le domaine
        # membre reste utilisé pour le comptage des membres.
        sections = Section.search(
            section_domain,
            order="name, id",
            limit=self.MAX_BROWSER_SECTION_ROWS,
        )
        for record in sections:
            count = self.env["kiiraaye.partisan"].search_count(
                list(member_domain) + [("section_ids", "=", record.id)]
            )
            status = self.env["kiiraaye.effectif.status"].get_for_count(count)
            rows.append(
                {
                    "id": record.id,
                    "name": record.name,
                    "type": self._selection_label(
                        Section._fields["type_section"],
                        record.type_section,
                    ),
                    "members": int(count or 0),
                    "status": status.name if status else "",
                    "state": self._selection_label(
                        Section._fields["state"],
                        record.state,
                    ),
                }
            )
        rows.sort(key=lambda row: (-row["members"], row["name"]))
        return rows

    def _get_top_organisation_rows(self, organisation_domain, member_domain, Organisation):
        """Retourne quelques organisations avec un comptage borné.

        Le regroupement direct sur organisation_ids (Many2many) est évité afin
        de rester compatible avec l'ORM Odoo 19 et avec les gros volumes.
        """
        rows = []
        organisations = Organisation.search(
            organisation_domain,
            order="name, id",
            limit=self.MAX_BROWSER_ORGANISATION_ROWS,
        )
        for record in organisations:
            count = self.env["kiiraaye.partisan"].search_count(
                list(member_domain) + [("organisation_ids", "=", record.id)]
            )
            status = self.env["kiiraaye.effectif.status"].get_for_count(count)
            rows.append(
                {
                    "id": record.id,
                    "name": record.name,
                    "type": record.type_id.name if record.type_id else "",
                    "level": record.niveau or 0,
                    "members": int(count or 0),
                    "status": status.name if status else "",
                }
            )
        rows.sort(key=lambda row: (-row["members"], row["name"]))
        return rows

    # Position indicative des 14 régions sur la carte SVG du Sénégal.
    # Les positions servent uniquement à placer les repères visuels; les données
    # territoriales restent issues du référentiel Kiiraaye.
    REGIONAL_MAP_POSITIONS = {
        "DAKAR": (6.6, 44.6),
        "THIES": (14.6, 43.1),
        "DIOURBEL": (24.9, 46.1),
        "FATICK": (22.0, 52.7),
        "KAOLACK": (27.1, 56.7),
        "KAFFRINE": (35.0, 57.7),
        "LOUGA": (25.0, 25.7),
        "SAINT-LOUIS": (21.0, 16.8),
        "MATAM": (69.2, 24.9),
        "TAMBACOUNDA": (61.6, 64.7),
        "KEDOUGOU": (85.3, 90.4),
        "KOLDA": (44.0, 83.4),
        "SEDHIOU": (34.9, 87.2),
        "ZIGUINCHOR": (24.3, 89.9),
    }

    REGIONAL_REFERENCE_STATS = {
        "DAKAR": {"population": 4004426, "electors": 1829821},
        "ZIGUINCHOR": {"population": 617567, "electors": 308259},
        "DIOURBEL": {"population": 2080333, "electors": 635793},
        "SAINT-LOUIS": {"population": 1202441, "electors": 563642},
        "TAMBACOUNDA": {"population": 987152, "electors": 287149},
        "KAOLACK": {"population": 1336720, "electors": 464437},
        "THIES": {"population": 2463677, "electors": 1003310},
        "LOUGA": {"population": 1125908, "electors": 460639},
        "FATICK": {"population": 906918, "electors": 348525},
        "KOLDA": {"population": 914798, "electors": 265611},
        "MATAM": {"population": 831630, "electors": 315863},
        "KAFFRINE": {"population": 820405, "electors": 268124},
        "KEDOUGOU": {"population": 245147, "electors": 72413},
        "SEDHIOU": {"population": 589266, "electors": 210264},
    }
    REGIONAL_REFERENCE_SOURCE = (
        "Population : ANSD / RGPH-5 2023 ; "
        "électeurs inscrits : DGE, carte électorale 2024."
    )

    NATIONAL_REFERENCE_SOURCE = (
        "Population nationale : somme des références régionales ANSD / RGPH-5 2023 ; "
        "électeurs inscrits : somme des références régionales DGE 2024."
    )

    def _national_reference_stats(self):
        population = sum(
            item.get("population", 0)
            for item in self.REGIONAL_REFERENCE_STATS.values()
        )
        electors = sum(
            item.get("electors", 0)
            for item in self.REGIONAL_REFERENCE_STATS.values()
        )
        return {
            "population": population,
            "electors": electors,
        }


    @staticmethod
    def _normalize_geo_name(value):
        value = unicodedata.normalize("NFKD", value or "")
        value = "".join(ch for ch in value if not unicodedata.combining(ch))
        return " ".join(value.upper().replace("_", " ").split())

    def _regional_external_stats(self, region):
        stats = self.REGIONAL_REFERENCE_STATS.get(
            self._normalize_geo_name(region.name)
        )
        if not stats:
            return {
                "population": 0,
                "electors": 0,
                "electoral_ratio_pct": 0.0,
                "member_elector_ratio_pct": 0.0,
                "member_population_ratio_pct": 0.0,
                "reference_available": False,
            }
        return {
            "population": stats["population"],
            "electors": stats["electors"],
            "electoral_ratio_pct": round(
                stats["electors"] / stats["population"] * 100, 2
            )
            if stats["population"]
            else 0.0,
            "member_elector_ratio_pct": 0.0,
            "member_population_ratio_pct": 0.0,
            "reference_available": True,
        }

    def _get_section_geography_overview(
        self,
        Geography,
        Section,
        Partisan,
        section_domain=None,
        member_domain=None,
    ):
        """Vue région > département > commune avec sections et membres."""
        senegal = self.env["res.country"].search([("code", "=", "SN")], limit=1)
        active_geo_domain = [("active", "=", True)]
        if senegal:
            active_geo_domain.append(("country_id", "=", senegal.id))

        regions = Geography.search(
            active_geo_domain + [("niveau", "=", "niveau1")],
            order="name, id",
        )
        departments = Geography.search(
            active_geo_domain + [("niveau", "=", "niveau2")],
            order="name, id",
        )
        communes = Geography.search(
            active_geo_domain + [("niveau", "=", "niveau3")],
            order="name, id",
        )

        def grouped_counts(model, domain, field_name):
            return {
                record.id: int(count or 0)
                for record, count in model._read_group(
                    domain,
                    [field_name],
                    ["__count"],
                    order="__count DESC",
                )
                if record
            }

        section_active_domain = list(section_domain or [("active", "=", True)])
        section_open_domain = section_active_domain + [("state", "=", "ouverte")]
        member_active_domain = list(member_domain or [("active", "=", True)])

        section_region = grouped_counts(Section, section_active_domain, "region_id")
        section_region_open = grouped_counts(Section, section_open_domain, "region_id")
        section_department = grouped_counts(Section, section_active_domain, "departement_id")
        section_department_open = grouped_counts(Section, section_open_domain, "departement_id")
        section_commune = grouped_counts(Section, section_active_domain, "commune_id")
        section_commune_open = grouped_counts(Section, section_open_domain, "commune_id")

        coordinator_domains = {
            "region": [
                ("active", "=", True),
                ("type_section", "=", "regionale"),
                ("region_id", "!=", False),
            ],
            "department": [
                ("active", "=", True),
                ("type_section", "=", "departementale"),
                ("departement_id", "!=", False),
            ],
            "commune": [
                ("active", "=", True),
                ("type_section", "=", "communale"),
                ("commune_id", "!=", False),
            ],
        }
        coordinator_maps = {
            "region": defaultdict(list),
            "department": defaultdict(list),
            "commune": defaultdict(list),
        }

        def get_coordinator_name(coordination):
            # Source principale : coordonnateur explicitement renseigné.
            if coordination.cordonnateur_id:
                return coordination.cordonnateur_id.nom_complet or ""

            # Compatibilité avec les bureaux : si le champ coordonnateur
            # n'est pas renseigné, le titulaire du poste COORD est utilisé.
            bureau_line = coordination.bureau_ligne_ids.filtered(
                lambda line: (
                    line.active
                    and line.position_id
                    and line.position_id.code == "COORD"
                    and line.partisan_id
                )
            )[:1]
            return bureau_line.partisan_id.nom_complet if bureau_line else ""

        for level, domain in coordinator_domains.items():
            if senegal:
                domain.append(("country_id", "=", senegal.id))
            field_name = {
                "region": "region_id",
                "department": "departement_id",
                "commune": "commune_id",
            }[level]
            for coordination in Section.search(domain, order=f"{field_name}, id"):
                coordinator_name = get_coordinator_name(coordination)
                geography = getattr(coordination, field_name)
                if geography and coordinator_name:
                    if coordinator_name not in coordinator_maps[level][geography.id]:
                        coordinator_maps[level][geography.id].append(
                            coordinator_name
                        )

        # Deuxième filet : certains paramétrages peuvent avoir une
        # coordination créée avec le bon niveau géographique mais une ligne
        # COORD enregistrée dans le bureau d'une structure apparentée.
        # On tente alors de retrouver le premier titulaire COORD actif sur
        # la même zone géographique.
        fallback_field_by_level = {
            "region": "region_id",
            "department": "departement_id",
            "commune": "commune_id",
        }
        for level, field_name in fallback_field_by_level.items():
            geographies = {
                geography_id
                for geography_id in coordinator_maps[level]
            }
            if level == "region":
                geographies.update(region.id for region in regions)
            elif level == "department":
                geographies.update(department.id for department in departments)
            else:
                geographies.update(commune.id for commune in communes)

            for geography_id in geographies:
                if coordinator_maps[level].get(geography_id):
                    continue
                candidates = Section.search(
                    [
                        ("active", "=", True),
                        ("country_id.code", "=", "SN"),
                        (field_name, "=", geography_id),
                        ("bureau_ligne_ids.active", "=", True),
                        ("bureau_ligne_ids.position_id.code", "=", "COORD"),
                    ],
                    order="id",
                    limit=20,
                )
                for candidate in candidates:
                    coordinator_name = get_coordinator_name(candidate)
                    if coordinator_name:
                        coordinator_maps[level][geography_id].append(coordinator_name)
                        break

        regional_coordinators = {
            geo_id: " · ".join(names)
            for geo_id, names in coordinator_maps["region"].items()
        }
        department_coordinators = {
            geo_id: " · ".join(names)
            for geo_id, names in coordinator_maps["department"].items()
        }
        commune_coordinators = {
            geo_id: " · ".join(names)
            for geo_id, names in coordinator_maps["commune"].items()
        }

        member_region = grouped_counts(Partisan, member_active_domain, "region_id")
        member_department = grouped_counts(Partisan, member_active_domain, "departement_id")
        member_commune = grouped_counts(Partisan, member_active_domain, "commune_id")

        departments_by_region = defaultdict(list)
        for department in departments:
            current = department.parent_id
            while current and current.niveau != "niveau1":
                current = current.parent_id
            if current:
                departments_by_region[current.id].append(department)

        communes_by_department = defaultdict(list)
        for commune in communes:
            current = commune.parent_id
            while current and current.niveau != "niveau2":
                current = current.parent_id
            if current:
                communes_by_department[current.id].append(commune)

        overview = []
        for region in regions:
            external = self._regional_external_stats(region)
            region_members = member_region.get(region.id, 0)
            external["member_elector_ratio_pct"] = round(
                region_members / external["electors"] * 100, 2
            ) if external["electors"] else 0.0
            external["member_population_ratio_pct"] = round(
                region_members / external["population"] * 100, 2
            ) if external["population"] else 0.0

            department_rows = []
            for department in departments_by_region.get(region.id, []):
                commune_rows = [
                    {
                        "id": commune.id,
                        "name": commune.name,
                        "sections": section_commune.get(commune.id, 0),
                        "sections_open": section_commune_open.get(commune.id, 0),
                        "members": member_commune.get(commune.id, 0),
                        "coordinator": commune_coordinators.get(commune.id, ""),
                    }
                    for commune in communes_by_department.get(department.id, [])
                ]
                department_rows.append(
                    {
                        "id": department.id,
                        "name": department.name,
                        "sections": section_department.get(department.id, 0),
                        "sections_open": section_department_open.get(department.id, 0),
                        "members": member_department.get(department.id, 0),
                        "coordinator": department_coordinators.get(department.id, ""),
                        "communes": len(commune_rows),
                        "communes_occupied": sum(
                            1 for commune in commune_rows if commune["sections"]
                        ),
                        "commune_rows": commune_rows,
                    }
                )

            overview.append(
                {
                    "id": region.id,
                    "name": region.name,
                    "departments": len(department_rows),
                    "departments_occupied": sum(
                        1 for item in department_rows if item["sections"]
                    ),
                    "communes": sum(item["communes"] for item in department_rows),
                    "communes_occupied": sum(
                        1
                        for item in department_rows
                        for commune in item["commune_rows"]
                        if commune["sections"]
                    ),
                    "sections": section_region.get(region.id, 0),
                    "sections_open": section_region_open.get(region.id, 0),
                    "members": region_members,
                    "coordinator": regional_coordinators.get(region.id, ""),
                    "population": external["population"],
                    "electors": external["electors"],
                    "electoral_ratio_pct": external["electoral_ratio_pct"],
                    "member_elector_ratio_pct": external["member_elector_ratio_pct"],
                    "member_population_ratio_pct": external["member_population_ratio_pct"],
                    "reference_available": external["reference_available"],
                    "departments_rows": department_rows,
                }
            )

        return overview

    def _get_diaspora_country_overview(
        self,
        Section,
        Partisan,
        section_domain,
        member_domain,
    ):
        grouped = Section._read_group(
            section_domain,
            ["country_id"],
            ["__count"],
            order="__count DESC",
        )

        rows = []
        for country, section_count in grouped:
            if not country:
                continue
            member_count = Partisan.search_count(
                list(member_domain) + [
                    ("section_ids.country_id", "=", country.id),
                ]
            )
            rows.append({
                "id": country.id,
                "name": country.name,
                "sections": int(section_count or 0),
                "members": int(member_count or 0),
            })

        rows.sort(
            key=lambda row: (-row["members"], -row["sections"], row["name"])
        )
        return rows, len(rows)

    def _get_top_member_geographies(self, Partisan):
        domain = [("active", "=", True)]

        def top_rows(field_name, label):
            rows = []
            for record, count in Partisan._read_group(
                domain,
                [field_name],
                ["__count"],
                limit=10,
                order="__count DESC",
            ):
                if record:
                    rows.append(
                        {
                            "id": record.id,
                            "name": record.name,
                            "members": int(count or 0),
                            "level": label,
                        }
                    )
            return rows

        return {
            "regions": top_rows("region_id", "Région"),
            "departments": top_rows("departement_id", "Département"),
            "communes": top_rows("commune_id", "Commune"),
        }

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

    @staticmethod
    def _election_row(
        result,
        members,
        level,
        geography_id=None,
        geography_name="",
    ):
        voters = int(result.get("voters") or 0) if result else None
        registered = int(result.get("registered_voters") or 0) if result else None
        valid = int(result.get("valid_votes") or 0) if result else None
        null_votes = int(result.get("null_votes") or 0) if result else None
        diomaye_votes = (
            int(result.get("diomaye_president_votes") or 0)
            if result
            else None
        )

        participation_pct = (
            round(voters / registered * 100, 2) if registered else None
        )
        diomaye_pct = (
            round(diomaye_votes / valid * 100, 2) if valid else None
        )
        members_pct_of_voters = (
            round(members / voters * 100, 2) if voters else None
        )
        gap_pct = (
            round((members - voters) / voters * 100, 2) if voters else None
        )

        if gap_pct is None:
            gap_class = "missing"
            gap_label = "Donnée électorale manquante"
        elif gap_pct >= -5:
            gap_class = "green"
            gap_label = "Écart faible"
        elif gap_pct >= -20:
            gap_class = "yellow"
            gap_label = "Écart modéré"
        elif gap_pct >= -40:
            gap_class = "orange"
            gap_label = "Écart marqué"
        else:
            gap_class = "red"
            gap_label = "Écart élevé"

        return {
            "id": geography_id,
            "name": geography_name,
            "level": level,
            "registered_voters": registered,
            "voters": voters,
            "null_votes": null_votes,
            "valid_votes": valid,
            "diomaye_president_votes": diomaye_votes,
            "diomaye_president_pct": diomaye_pct,
            "participation_pct": participation_pct,
            "members": int(members or 0),
            "members_pct_of_voters": members_pct_of_voters,
            "gap_pct": gap_pct,
            "gap_class": gap_class,
            "gap_label": gap_label,
            "data_available": bool(result),
        }

    def _historical_election_overview(self, Partisan, Geography):
        Election = self.env["kiiraaye.election"]
        Result = self.env["kiiraaye.election.result"]

        election = Election.search(
            [("active", "=", True)],
            order="date desc, id desc",
            limit=1,
        )
        if not election:
            return {
                "available": False,
                "election": False,
                "global": False,
                "regions": [],
                "message": _(
                    "Aucune élection historique n'est configurée. "
                    "Ajoutez un scrutin dans Configuration → Historique des élections."
                ),
            }

        # Charge automatiquement les résultats officiels disponibles pour
        # la présidentielle 2024 avant de construire les agrégats territoriaux.
        Result.ensure_presidential_2024_department_results(election)

        direct_results = Result.search([
            ("election_id", "=", election.id),
            ("scope", "=", "geographique"),
        ])
        direct = {
            row.geographie_id.id: {
                "geographie_id": row.geographie_id.id,
                "name": row.geographie_id.name,
                "registered_voters": row.registered_voters,
                "voters": row.voters,
                "null_votes": row.null_votes,
                "valid_votes": row.valid_votes,
                "diomaye_president_votes": row.diomaye_president_votes,
            }
            for row in direct_results
            if row.geographie_id
        }

        global_result = Result.search([
            ("election_id", "=", election.id),
            ("scope", "=", "global"),
        ], order="id desc", limit=1)

        global_data = False
        if global_result:
            global_data = self._election_row(
                {
                    "registered_voters": global_result.registered_voters,
                    "voters": global_result.voters,
                    "null_votes": global_result.null_votes,
                    "valid_votes": global_result.valid_votes,
                    "diomaye_president_votes": global_result.diomaye_president_votes,
                },
                0,
                "Global",
                None,
                "Sénégal",
            )
            global_data.update({
                "all_parties_votes": int(global_result.valid_votes or 0),
                "valid_pct_of_valid_votes": 100.0,
                "result_label": "Ensemble des candidats / listes",
            })

        def grouped_members(field_name):
            return {
                record.id: int(count or 0)
                for record, count in Partisan._read_group(
                    [("active", "=", True)],
                    [field_name],
                    ["__count"],
                    order="__count DESC",
                )
                if record
            }

        member_region = grouped_members("region_id")
        member_department = grouped_members("departement_id")
        member_commune = grouped_members("commune_id")

        senegal = self.env["res.country"].search([("code", "=", "SN")], limit=1)
        geo_domain = [("active", "=", True)]
        if senegal:
            geo_domain.append(("country_id", "=", senegal.id))

        regions = Geography.search(
            geo_domain + [("niveau", "=", "niveau1")],
            order="name, id",
        )
        departments = Geography.search(
            geo_domain + [("niveau", "=", "niveau2")],
            order="name, id",
        )
        communes = Geography.search(
            geo_domain + [("niveau", "=", "niveau3")],
            order="name, id",
        )

        children = defaultdict(list)
        for geography in departments | communes:
            if geography.parent_id:
                children[geography.parent_id.id].append(geography)

        def merge_results(results):
            results = [item for item in results if item]
            if not results:
                return None
            return {
                "registered_voters": sum(
                    item["registered_voters"] for item in results
                ),
                "voters": sum(item["voters"] for item in results),
                "null_votes": sum(item["null_votes"] for item in results),
                "valid_votes": sum(item["valid_votes"] for item in results),
                "diomaye_president_votes": sum(
                    item["diomaye_president_votes"] for item in results
                ),
            }

        department_effective = {}
        for department in departments:
            if department.id in direct:
                department_effective[department.id] = direct[department.id]
            else:
                department_effective[department.id] = merge_results(
                    [
                        direct.get(commune.id)
                        for commune in children.get(department.id, [])
                        if commune.niveau == "niveau3"
                    ]
                )

        region_effective = {}
        for region in regions:
            if region.id in direct:
                region_effective[region.id] = direct[region.id]
            else:
                region_effective[region.id] = merge_results(
                    [
                        department_effective.get(department.id)
                        for department in children.get(region.id, [])
                        if department.niveau == "niveau2"
                    ]
                )

        department_rows_by_id = {}
        for department in departments:
            department_rows_by_id[department.id] = self._election_row(
                department_effective.get(department.id),
                member_department.get(department.id, 0),
                "Département",
                department.id,
                department.name,
            )

        commune_rows_by_id = {}
        for commune in communes:
            commune_rows_by_id[commune.id] = self._election_row(
                direct.get(commune.id),
                member_commune.get(commune.id, 0),
                "Commune",
                commune.id,
                commune.name,
            )

        # Une seule ligne par région, avec ses départements et communes
        # regroupés dessous. Cela évite de répéter les totaux régionaux.
        region_rows = []
        for region in regions:
            row = self._election_row(
                region_effective.get(region.id),
                member_region.get(region.id, 0),
                "Région",
                region.id,
                region.name,
            )
            row["departments"] = []
            for department in children.get(region.id, []):
                if department.niveau != "niveau2":
                    continue
                department_row = dict(department_rows_by_id.get(department.id, {}))
                department_row["communes"] = [
                    dict(commune_rows_by_id[commune.id])
                    for commune in children.get(department.id, [])
                    if commune.niveau == "niveau3" and commune.id in commune_rows_by_id
                ]
                row["departments"].append(department_row)
            region_rows.append(row)

        return {
            "available": bool(global_data or direct_results),
            "election": {
                "id": election.id,
                "name": election.name,
                "date": election.date.strftime("%d/%m/%Y") if election.date else "",
                "type": self._selection_label(
                    Election._fields["election_type"],
                    election.election_type,
                ),
                "source": election.source,
                "source_url": election.source_url or "",
            },
            "global": global_data,
            "regions": region_rows,
            "message": _(
                "Les lignes sont regroupées par région et contiennent les "
                "départements puis les communes. Les données électorales "
                "territoriales absentes restent en gris. Les membres Kiiraay "
                "sont les membres actifs actuels du référentiel."
            ),
        }

    @api.model
    def get_dashboard_data(self, filters=None):
        self._check_dashboard_access()
        filters = filters or {}
        current_view = filters.get("view", "section")
        section_scope = filters.get("section_scope", "national")
        if section_scope not in ("national", "diaspora"):
            section_scope = "national"

        Section = self.env["kiiraaye.section"]
        Organisation = self.env["kiiraaye.organisation"]
        Partisan = self.env["kiiraaye.partisan"]
        Geography = self.env["kiiraaye.geographie"]

        section_domain = self._section_scope_domain(section_scope, filters)
        member_domain = self._member_scope_domain(section_scope, filters)
        organisation_domain = self._organisation_domain(filters)
        effectif = self._effectif_overview()

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
        national_reference = self._national_reference_stats()
        national_population = national_reference["population"]
        national_electors = national_reference["electors"]
        national_member_population_ratio_pct = (
            round(current_member_count / national_population * 100, 2)
            if national_population
            else 0.0
        )
        national_member_elector_ratio_pct = (
            round(current_member_count / national_electors * 100, 2)
            if national_electors
            else 0.0
        )
        total_member_count = Partisan.search_count([])
        inactive_member_count = Partisan.search_count([("active", "=", False)])

        section_rows = []
        organisation_rows = []
        coordinator_rows = []
        ralliement_rows = []
        member_creation = []
        geography_levels = []
        geography_rows = []
        section_geography_overview = []
        diaspora_country_rows = []
        diaspora_country_count = 0
        top_member_geographies = {"regions": [], "departments": [], "communes": []}

        if current_view == "section" and section_scope == "national":
            section_geography_overview = self._get_section_geography_overview(
                Geography,
                Section,
                Partisan,
                section_domain=section_domain,
                member_domain=member_domain,
            )
            top_member_geographies = self._get_top_member_geographies(Partisan)

        if current_view == "section" and section_scope == "diaspora":
            diaspora_country_rows, diaspora_country_count = self._get_diaspora_country_overview(
                Section,
                Partisan,
                section_domain,
                member_domain,
            )

        if current_view == "section":
            section_rows = self._get_top_section_rows(
                section_domain,
                member_domain,
                Section,
            )

        # Coordonnateurs territoriaux : source = champ explicite ou titulaire
        # du poste COORD dans le bureau.
        if section_scope == "national":
            territorial_sections = Section.search(
                [
                    ("active", "=", True),
                    ("country_id.code", "=", "SN"),
                    ("type_section", "in", ("regionale", "departementale", "communale")),
                ],
                order="type_section, name, id",
                limit=1000,
            )
            for coordination in territorial_sections:
                coordinator = coordination.cordonnateur_id
                if not coordinator:
                    line = coordination.bureau_ligne_ids.filtered(
                        lambda item: (
                            item.active
                            and item.position_id
                            and item.position_id.code == "COORD"
                            and item.partisan_id
                        )
                    )[:1]
                    coordinator = line.partisan_id if line else False
                if not coordinator:
                    continue
                coordinator_rows.append(
                    {
                        "id": coordination.id,
                        "type": self._selection_label(
                            Section._fields["type_section"],
                            coordination.type_section,
                        ),
                        "name": coordination.name,
                        "coordinator": coordinator.nom_complet,
                    }
                )

        Ralliement = self.env["kiiraaye.ralliement"]
        ralliement_labels = dict(Ralliement._fields["type_ralliement"].selection)
        for type_value in ("parti", "organisation", "association", "mouvement", "cooperative"):
            count = Ralliement.search_count(
                [("active", "=", True), ("type_ralliement", "=", type_value)]
            )
            member_count = Partisan.search_count(
                [
                    ("active", "=", True),
                    ("ralliement_ids.type_ralliement", "=", type_value),
                ]
            )
            ralliement_rows.append(
                {
                    "type": type_value,
                    "label": ralliement_labels.get(type_value, type_value),
                    "count": count,
                    "members": member_count,
                }
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
        last_creation_value = values[-1] if values else 0
        projection_base = (
            fields.Datetime.now().replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        )
        for step in range(1, 7):
            projected_additions = max(
                0,
                round(last_creation_value + trend * step),
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
                self._section_scope_domain(section_scope, {}),
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

        section_geo_region_count = len(section_geography_overview)
        section_geo_region_occupied = sum(
            1 for row in section_geography_overview if row["sections"]
        )
        section_geo_department_total = sum(
            row["departments"] for row in section_geography_overview
        )
        section_geo_department_occupied = sum(
            row["departments_occupied"] for row in section_geography_overview
        )
        section_geo_commune_total = sum(
            row["communes"] for row in section_geography_overview
        )
        section_geo_commune_occupied = sum(
            row["communes_occupied"]
            for row in section_geography_overview
        )

        regional_map = []
        department_map = []
        for region in section_geography_overview:
            position = self.REGIONAL_MAP_POSITIONS.get(
                self._normalize_geo_name(region["name"])
            )
            if not position:
                continue
            communes_total = int(region.get("communes") or 0)
            communes_occupied = int(region.get("communes_occupied") or 0)
            departments_total = int(region.get("departments") or 0)
            departments_occupied = int(region.get("departments_occupied") or 0)
            if communes_total:
                territorial_coverage_pct = round(
                    communes_occupied / communes_total * 100, 2
                )
            elif departments_total:
                territorial_coverage_pct = round(
                    departments_occupied / departments_total * 100, 2
                )
            else:
                territorial_coverage_pct = 0.0
            regional_map.append({
                "id": region["id"],
                "name": region["name"],
                "map_x": position[0],
                "map_y": position[1],
                "sections": region["sections"],
                "members": region["members"],
                "departments_total": departments_total,
                "departments_occupied": departments_occupied,
                "communes_total": communes_total,
                "communes_occupied": communes_occupied,
                "territorial_coverage_pct": territorial_coverage_pct,
            })

            dept_rows = region.get("departments_rows") or []
            count = len(dept_rows)
            for idx, department in enumerate(dept_rows):
                col = idx % 3
                row = idx // 3
                dx = (col - 1) * 3.4
                dy = (row - (max(0, count - 1) / 6.0)) * 4.2
                department_map.append({
                    "id": department["id"],
                    "name": department["name"],
                    "region_id": region["id"],
                    "map_x": max(3, min(96, position[0] + dx)),
                    "map_y": max(4, min(96, position[1] + dy)),
                    "sections": department["sections"],
                })

        if section_scope == "national":
            national_country = self.env["res.country"].search(
                [("code", "=", "SN")],
                limit=1,
            )
            if national_country:
                region_total = self.OFFICIAL_SENEGAL_TOTALS["regions"]
                department_total = self.OFFICIAL_SENEGAL_TOTALS["departments"]
                commune_total = self.OFFICIAL_SENEGAL_TOTALS["communes"]
            else:
                region_total = department_total = commune_total = 0
            region_occupied = section_geo_region_occupied
            department_occupied = section_geo_department_occupied
            commune_occupied = section_geo_commune_occupied
        else:
            region_total = department_total = commune_total = 0
            region_occupied = department_occupied = commune_occupied = 0

        return {
            "company": {
                "id": self.env.company.id,
                "name": self.env.company.name,
            },
            "effectif": effectif,
            "section_scope": section_scope,
            "section_scope_label": (
                "Sections nationales"
                if section_scope == "national"
                else "Sections diaspora"
            ),
            "national_reference": {
                "population": national_population,
                "electors": national_electors,
                "member_population_ratio_pct": national_member_population_ratio_pct,
                "member_elector_ratio_pct": national_member_elector_ratio_pct,
                "source": self.NATIONAL_REFERENCE_SOURCE,
            },
            "geography_scope": {
                "regions": {
                    "occupied": region_occupied,
                    "total": region_total,
                },
                "departments": {
                    "occupied": department_occupied,
                    "total": department_total,
                },
                "communes": {
                    "occupied": commune_occupied,
                    "total": commune_total,
                },
            },
            "diaspora": {
                "countries_covered": diaspora_country_count,
                "countries": diaspora_country_rows,
            },
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
                "region_count": region_occupied,
                "region_total": region_total,
                "department_count": department_occupied,
                "department_total": department_total,
                "commune_count": commune_occupied,
                "commune_total": commune_total,
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
            "coordinators": coordinator_rows,
            "ralliements": ralliement_rows,
            "section_geography_overview": section_geography_overview,
            "regional_map": regional_map,
            "department_map": department_map,
            "official_senegal_totals": self.OFFICIAL_SENEGAL_TOTALS,
            "top_member_geographies": top_member_geographies,
            "regional_reference_source": self.REGIONAL_REFERENCE_SOURCE,
            "geography_rows": geography_rows,
            "geography_levels": geography_levels,
            "member_creation": member_creation,
            "member_projection": projection,
            "projection_type": (
                "Projection descriptive de l'évolution des effectifs "
                "à partir de la tendance des créations de membres."
            ),
            "historical_election": self._historical_election_overview(Partisan, Geography),
        }
