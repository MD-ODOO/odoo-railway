from odoo import api, fields, models, _
from odoo.exceptions import UserError, ValidationError


class KiiraayeDemoDataWizard(models.TransientModel):
    _name = "kiiraaye.demo.data.wizard"
    _description = "Génération de données de démonstration Kiiraaye"

    section_count = fields.Integer(
        string="Nombre de sections",
        default=200,
        required=True,
    )
    member_count = fields.Integer(
        string="Nombre de membres",
        default=500,
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
        """Retourne la hiérarchie réelle Sénégal -> commune -> village."""
        Geo = self.env["kiiraaye.geographie"].sudo()

        regions = Geo.search([
            ("country_id", "=", country.id),
            ("niveau", "=", "niveau1"),
            ("active", "=", True),
        ], order="name, id")
        departments = Geo.search([
            ("country_id", "=", country.id),
            ("niveau", "=", "niveau2"),
            ("active", "=", True),
        ], order="name, id")
        communes = Geo.search([
            ("country_id", "=", country.id),
            ("niveau", "=", "niveau3"),
            ("active", "=", True),
        ], order="name, id")

        if not regions or not departments or not communes:
            raise UserError(_("Le référentiel réel du Sénégal est incomplet. Chargez d'abord les régions, départements et communes."))

        # Ne pas fabriquer de quartier. On charge uniquement les villages
        # réels correspondants aux communes depuis GalsenAPI, par pages de 80.
        quarters = Geo.search([
            ("country_id", "=", country.id),
            ("niveau", "=", "niveau5"),
            ("active", "=", True),
        ], order="parent_id, name, id")

        existing_galsen_count = Geo.search_count([
            ("country_id", "=", country.id),
            ("niveau", "=", "niveau5"),
            ("active", "=", True),
            ("source_uid", "like", "GALSEN-VILLAGE-%"),
        ])
        if existing_galsen_count < self.section_count:
            # Les villages GalsenAPI référencent la commune avec son
            # identifiant GalsenAPI, conservé dans kiiraaye.geographie.code.
            communes_map = {}
            for record in communes:
                try:
                    communes_map[int(record.code)] = record
                except (TypeError, ValueError):
                    continue

            if not communes_map:
                raise UserError(
                    _("Aucun identifiant GalsenAPI exploitable n'est disponible pour les communes du Sénégal.")
                )

            country._load_senegal_villages_galsen(
                communes_map,
                page_size=80,
                limit=self.section_count,
            )
            quarters = Geo.search([
                ("country_id", "=", country.id),
                ("niveau", "=", "niveau5"),
                ("active", "=", True),
            ], order="parent_id, name, id")

        return regions, departments, communes, quarters

    def _clear_existing_demo(self):
        Partisan = self.env["kiiraaye.partisan"].sudo()
        Section = self.env["kiiraaye.section"].sudo()
        Geo = self.env["kiiraaye.geographie"].sudo()

        demo_members = Partisan.search([("is_demo_data", "=", True)])
        demo_sections = Section.search([("is_demo_data", "=", True)])

        if demo_members:
            demo_members.unlink()
        if demo_sections:
            demo_sections.unlink()

        # Nettoyage des anciennes hiérarchies fictives générées par les
        # versions précédentes du wizard.
        demo_geo = Geo.search([
            ("source_uid", "in", [
                "DEMO-KIIRAAYE-REGION",
                "DEMO-KIIRAAYE-DEPARTEMENT",
                "DEMO-KIIRAAYE-COMMUNE",
                "DEMO-KIIRAAYE-PAYS",
            ])
        ])
        demo_quartiers = Geo.search([
            ("source_uid", "like", "DEMO-KIIRAAYE-QUARTIER-%")
        ])
        demo_locales = Geo.search([
            ("source_uid", "like", "DEMO-KIIRAAYE-LOCAL-%")
        ])

        if demo_quartiers:
            demo_quartiers.unlink()
        if demo_locales:
            demo_locales.unlink()
        if demo_geo:
            demo_geo.unlink()

    def action_generate(self):
        self.ensure_one()
        country = self._get_demo_country()

        if self.replace_existing:
            self._clear_existing_demo()

        regions, departments, communes, quarters = self._get_demo_hierarchy(country)
        Section = self.env["kiiraaye.section"].sudo()
        Partisan = self.env["kiiraaye.partisan"].sudo()

        # Les sections communales sont distribuées sur les vrais quartiers
        # ANSD déjà présents dans le référentiel du Sénégal.
        available_quarters = quarters
        if self.section_count > len(available_quarters):
            raise UserError(
                _(
                    "Le nombre demandé (%s) dépasse le nombre de quartiers / unités "
                    "locales réels disponibles (%s)."
                ) % (self.section_count, len(available_quarters))
            )

        existing_quarters = set(
            Section.search(
                [
                    ("active", "=", True),
                    ("type_section", "=", "communale"),
                    ("quartier_id", "in", available_quarters.ids),
                ]
            ).mapped("quartier_id").ids
        )

        selected_quarters = [
            quarter for quarter in available_quarters
            if quarter.id not in existing_quarters
        ][:self.section_count]

        if not selected_quarters:
            raise UserError(
                _(
                    "Aucun quartier réel disponible pour créer les sections de démonstration. "
                    "Les quartiers sélectionnés sont déjà occupés."
                )
            )

        section_vals = []
        for quarter in selected_quarters:
            commune = quarter.parent_id
            department = commune.parent_id if commune else False
            region = department.parent_id if department else False

            # Si le parent direct est un niveau intermédiaire, on remonte
            # jusqu'au niveau attendu par la section.
            while department and department.niveau != "niveau2":
                department = department.parent_id
            while region and region.niveau != "niveau1":
                region = region.parent_id

            if not commune or commune.niveau != "niveau3" or not department or not region:
                continue

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

        # Création des sections par lots de 80 pour limiter la durée de
        # chaque opération et rendre le traitement plus résilient.
        sections = Section.browse()
        batch_size = 80
        for start in range(0, len(section_vals), batch_size):
            sections |= Section.create(section_vals[start:start + batch_size])
            self.env.cr.commit()

        if not sections:
            raise UserError(_("Aucune section communale de démonstration n'a pu être créée."))

        # Référentiel diaspora réel : pays de résidence existant dans Odoo.
        # Aucun faux pays n'est créé. Une coordination diaspora est créée par
        # pays, dans la limite de 10 pays représentatifs.
        diaspora_codes = (
            "FR", "IT", "ES", "US", "BE", "CA", "GB", "DE", "CI", "MR"
        )
        diaspora_countries = self.env["res.country"].sudo().search(
            [("code", "in", diaspora_codes)],
            order="name, id",
        )
        diaspora_sections = self.env["kiiraaye.section"].sudo()
        created_diaspora = []
        for diaspora_country in diaspora_countries:
            if len(created_diaspora) >= 10:
                break
            exists = diaspora_sections.search(
                [
                    ("active", "=", True),
                    ("type_section", "=", "diaspora"),
                    ("country_id", "=", diaspora_country.id),
                ],
                limit=1,
            )
            if exists:
                continue
            created_diaspora.append(
                diaspora_sections.create(
                    {
                        "type_section": "diaspora",
                        "country_id": diaspora_country.id,
                        "is_demo_data": True,
                        "active": True,
                        "state": "ouverte",
                    }
                )
            )

        all_demo_sections = sections | diaspora_sections.browse([r.id for r in created_diaspora])

        # Identités de démonstration synthétiques : prénoms et noms de
        # famille courants au Sénégal. Elles ne correspondent pas à des
        # personnes réelles et aucun numéro d'identité réel n'est généré.
        senegal_first_names = [
            "Mamadou", "Ibrahima", "Abdoulaye", "Ousmane", "Cheikh",
            "Moussa", "Samba", "Modou", "Lamine", "Pape",
            "Moustapha", "Babacar", "Serigne", "Boubacar", "Amadou",
            "Alioune", "Malick", "Issa", "Souleymane", "El Hadji",
            "Khadim", "Tidiane", "Mountaga", "Mor", "Papa",
            "Matar", "Baye", "Ndiaga", "Seydou", "Birame",
            "Aïssatou", "Fatou", "Mariama", "Aminata", "Khady",
            "Astou", "Ndeye", "Sokhna", "Mame", "Coumba",
            "Awa", "Bineta", "Adama", "Rokhaya", "Diary",
            "Nabou", "Fama", "Seynabou", "Marème", "Ndèye",
            "Kiné", "Hawa", "Anta", "Penda", "Yacine",
            "Sokhna Awa", "Mame Diarra", "Fatoumata", "Aminata", "Binta",
            "Aïda", "Nafissatou", "Mame Fama", "Ramatoulaye", "Sokhna Khady",
        ]
        senegal_last_names = [
            "Diop", "Ndiaye", "Fall", "Ba", "Sow", "Sy", "Gueye",
            "Diallo", "Cissé", "Faye", "Seck", "Sarr", "Mbaye",
            "Thiam", "Kane", "Niang", "Lo", "Dieng", "Diouf",
            "Camara", "Touré", "Samb", "Ndao", "Wade", "Gningue",
            "Ndour", "Dia", "Kébé", "Sagna", "Bâ", "Tall",
            "Dème", "Badiane", "Coly", "Sonko", "Baldé", "Tine",
            "Kandé", "Mané", "Fofana", "Konaté", "Barry", "Sène",
            "Seck", "Cissé", "Gomis", "Sylla", "Khouma", "Sall",
        ]

        member_vals = []
        if not all_demo_sections:
            raise UserError(_("Aucune section de démonstration n'est disponible."))

        for index in range(1, self.member_count + 1):
            section = all_demo_sections[(index - 1) % len(all_demo_sections)]
            first_name = senegal_first_names[(index - 1) % len(senegal_first_names)]
            last_name = senegal_last_names[
                ((index - 1) // len(senegal_first_names)) % len(senegal_last_names)
            ]

            member_vals.append(
                {
                    "prenom": first_name,
                    "nom": last_name,
                    "country_id": section.country_id.id,
                    "region_id": section.region_id.id or False,
                    "departement_id": section.departement_id.id or False,
                    "commune_id": section.commune_id.id or False,
                    "quartier_id": section.quartier_id.id or False,
                    "lieu_naissance": (
                        section.commune_id.name
                        if section.commune_id
                        else section.country_id.name
                    ),
                    "active": True,
                    "is_demo_data": True,
                    "section_ids": [(6, 0, [section.id])],
                }
            )

        # Création par lots pour éviter une transaction HTTP trop lourde.
        batch_size = 80
        for start in range(0, len(member_vals), batch_size):
            Partisan.with_context(
                kiiraaye_demo_generation=True
            ).create(member_vals[start:start + batch_size])
            self.env.cr.commit()

        total_sections = len(sections) + len(created_diaspora)
        diaspora_names = ", ".join(
            record.country_id.name for record in created_diaspora
        )

        return {
            "type": "ir.actions.client",
            "tag": "display_notification",
            "params": {
                "title": _("Données de démonstration générées"),
                "message": _(
                    "%s sections communales rattachées aux vraies données géographiques "
                    "du Sénégal, %s coordinations diaspora et %s membres générés. "
                    "Pays diaspora : %s."
                )
                % (
                    len(sections),
                    len(created_diaspora),
                    self.member_count,
                    diaspora_names or _("aucun"),
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
