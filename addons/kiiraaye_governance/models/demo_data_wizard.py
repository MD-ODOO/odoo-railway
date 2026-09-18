from odoo import api, fields, models, _
from odoo.exceptions import UserError, ValidationError


class KiiraayeDemoDataWizard(models.TransientModel):
    _name = "kiiraaye.demo.data.wizard"
    _description = "Génération de données de démonstration Kiiraaye"

    section_count = fields.Integer(
        string="Nombre de sections",
        default=1000,
        required=True,
    )
    member_count = fields.Integer(
        string="Nombre de membres",
        default=10000,
        required=True,
    )
    quartier_prefix = fields.Char(
        string="Préfixe des quartiers",
        default="Quartier",
        required=True,
    )
    replace_existing = fields.Boolean(
        string="Remplacer les données de démo existantes",
        default=True,
    )

    @api.constrains("section_count", "member_count")
    def _check_quantities(self):
        for record in self:
            if record.section_count < 1 or record.section_count > 1_000_000:
                raise ValidationError(_("Le nombre de sections doit être compris entre 1 et 1 000 000."))
            if record.member_count < 1 or record.member_count > 5_000_000:
                raise ValidationError(_("Le nombre de membres doit être compris entre 1 et 5 000 000."))

    def _get_demo_country(self):
        country = self.env["res.country"].search(
            [("code", "=", "SN")],
            limit=1,
        )
        if not country:
            raise UserError(_("Le pays Sénégal (SN) est introuvable."))
        return country

    def _upsert_geo(self, country, source_uid, values):
        Geo = self.env["kiiraaye.geographie"].sudo()
        record = Geo.search(
            [
                ("country_id", "=", country.id),
                ("source_uid", "=", source_uid),
            ],
            limit=1,
        )
        if record:
            record.write(values)
            return record
        values = dict(values)
        values.update(
            {
                "country_id": country.id,
                "source_uid": source_uid,
                "active": True,
                "source": "Kiiraaye - Données de démonstration",
                "source_admin_level": "MANUAL",
            }
        )
        return Geo.create(values)

    def _get_demo_hierarchy(self, country):
        root = self.env["kiiraaye.geographie"].sudo().search(
            [
                ("country_id", "=", country.id),
                ("niveau", "=", "pays"),
            ],
            limit=1,
        )
        if not root:
            root = self._upsert_geo(
                country,
                "DEMO-KIIRAAYE-PAYS",
                {
                    "name": country.name,
                    "code": country.code,
                    "niveau": "pays",
                    "designation_locale": "Pays",
                },
            )

        region = self._upsert_geo(
            country,
            "DEMO-KIIRAAYE-REGION",
            {
                "name": "Région Démo",
                "code": "DEMO-R",
                "parent_id": root.id,
                "niveau": "niveau1",
                "designation_locale": "Région",
            },
        )
        department = self._upsert_geo(
            country,
            "DEMO-KIIRAAYE-DEPARTEMENT",
            {
                "name": "Département Démo",
                "code": "DEMO-D",
                "parent_id": region.id,
                "niveau": "niveau2",
                "designation_locale": "Département",
            },
        )
        commune = self._upsert_geo(
            country,
            "DEMO-KIIRAAYE-COMMUNE",
            {
                "name": "Commune Démo",
                "code": "DEMO-C",
                "parent_id": department.id,
                "niveau": "niveau3",
                "designation_locale": "Commune",
            },
        )
        return region, department, commune

    def _clear_existing_demo(self):
        Partisan = self.env["kiiraaye.partisan"].sudo()
        Section = self.env["kiiraaye.section"].sudo()
        Geo = self.env["kiiraaye.geographie"].sudo()

        demo_members = Partisan.search([("is_demo_data", "=", True)])
        demo_sections = Section.search([("is_demo_data", "=", True)])
        demo_quartiers = Geo.search(
            [("source_uid", "like", "DEMO-KIIRAAYE-QUARTIER-%")]
        )

        if demo_members:
            demo_members.unlink()
        if demo_sections:
            demo_sections.unlink()
        if demo_quartiers:
            demo_quartiers.unlink()

    def action_generate(self):
        self.ensure_one()
        country = self._get_demo_country()

        if self.replace_existing:
            self._clear_existing_demo()

        region, department, commune = self._get_demo_hierarchy(country)
        Geo = self.env["kiiraaye.geographie"].sudo()
        Section = self.env["kiiraaye.section"].sudo()
        Partisan = self.env["kiiraaye.partisan"].sudo()

        # 1 quartier = 1 section dans le jeu de données de démonstration.
        # Le nom est volontairement séquentiel : Quartier 1, Quartier 2, ...
        quarter_vals = []
        for index in range(1, self.section_count + 1):
            quarter_vals.append(
                {
                    "name": f"{self.quartier_prefix} {index}",
                    "code": f"DEMO-Q-{index:06d}",
                    "country_id": country.id,
                    "parent_id": commune.id,
                    "niveau": "niveau5",
                    "designation_locale": "Quartier",
                    "source": "Kiiraaye - Données de démonstration",
                    "source_uid": f"DEMO-KIIRAAYE-QUARTIER-{index:06d}",
                    "source_admin_level": "MANUAL",
                    "active": True,
                }
            )

        quarters = Geo.create(quarter_vals)

        section_vals = []
        for index, quarter in enumerate(quarters, start=1):
            section_vals.append(
                {
                    "type_section": "communale",
                    "country_id": country.id,
                    "region_id": region.id,
                    "departement_id": department.id,
                    "commune_id": commune.id,
                    "quartier_id": quarter.id,
                    "is_demo_data": True,
                    "active": True,
                    "state": "ouverte",
                }
            )
        sections = Section.create(section_vals)

        # Répartit les membres de façon cyclique sur les sections.
        # Chaque membre est rattaché directement à une section.
        member_vals = []
        for index in range(1, self.member_count + 1):
            section = sections[(index - 1) % len(sections)]
            member_vals.append(
                {
                    "prenom": "Membre",
                    "nom": f"Démo {index:07d}",
                    "country_id": country.id,
                    "region_id": section.region_id.id,
                    "departement_id": section.departement_id.id,
                    "commune_id": section.commune_id.id,
                    "quartier_id": section.quartier_id.id,
                    "active": True,
                    "is_demo_data": True,
                    "section_ids": [(6, 0, [section.id])],
                }
            )

        Partisan.with_context(
            kiiraaye_demo_generation=True
        ).create(member_vals)

        return {
            "type": "ir.actions.client",
            "tag": "display_notification",
            "params": {
                "title": _("Données de démonstration générées"),
                "message": _(
                    "%s sections et %s membres ont été créés. "
                    "Les quartiers sont nommés « %s 1 », « %s 2 », « %s 3 », etc."
                )
                % (
                    len(sections),
                    self.member_count,
                    self.quartier_prefix,
                    self.quartier_prefix,
                    self.quartier_prefix,
                ),
                "type": "success",
                "sticky": False,
            },
        }

    def action_clear(self):
        self.ensure_one()
        self._clear_existing_demo()
        return {
            "type": "ir.actions.client",
            "tag": "display_notification",
            "params": {
                "title": _("Données de démonstration supprimées"),
                "message": _("Les sections, membres et quartiers de démonstration ont été supprimés."),
                "type": "success",
                "sticky": False,
            },
        }
