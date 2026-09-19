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
        default=1200,
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
        """Retourne uniquement la hiérarchie déjà chargée dans Odoo.

        Le wizard de démonstration ne déclenche aucun chargement réseau.
        Les villages/quartiers réels doivent être chargés au préalable via
        l'import GalsenAPI en arrière-plan.
        """
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
            raise UserError(_(
                "Chargez d'abord les régions, départements et communes du Sénégal "
                "dans le Référentiel géographique."
            ))

        quarters = Geo.search([
            ("country_id", "=", country.id),
            ("niveau", "=", "niveau5"),
            ("active", "=", True),
        ], order="parent_id, name, id")

        if len(quarters) < self.section_count:
            raise UserError(_(
                "Chargez d'abord les villages / quartiers réels depuis GalsenAPI. "
                "%s unités locales sont disponibles, %s sont nécessaires pour la démo. "
                "Relancez l'import des villages puis recommencez la génération."
            ) % (len(quarters), self.section_count))

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
        demo_organisations = self.env["kiiraaye.organisation"].sudo().search([
            ("code", "like", "DEMO-KIIRAAYE-ORG-%")
        ])
        demo_professions = self.env["kiiraaye.profession"].sudo().search([
            ("code", "like", "DEMO-KIIRAAYE-PROF-%")
        ])

        if demo_quartiers:
            demo_quartiers.unlink()
        if demo_locales:
            demo_locales.unlink()
        if demo_geo:
            demo_geo.unlink()
        if demo_organisations:
            demo_organisations.unlink()
        if demo_professions:
            demo_professions.unlink()

    def action_generate(self):
        self.ensure_one()
        country = self._get_demo_country()

        if self.replace_existing:
            self._clear_existing_demo()

        regions, departments, communes, quarters = self._get_demo_hierarchy(country)
        Section = self.env["kiiraaye.section"].sudo()
        Partisan = self.env["kiiraaye.partisan"].sudo()
        BureauLine = self.env["kiiraaye.bureau.ligne"].sudo()
        Position = self.env["kiiraaye.position"].sudo()
        Organisation = self.env["kiiraaye.organisation"].sudo()
        OrganisationType = self.env["kiiraaye.organisation.type"].sudo()
        Profession = self.env["kiiraaye.profession"].sudo()

        positions = Position.search(
            [
                ("code", "in", ("COORD", "ORG", "COM", "MASS", "ELEC")),
                ("active", "=", True),
            ],
            order="sequence, id",
        )
        if len(positions) < 5:
            raise UserError(
                _("Les cinq postes standards du bureau doivent être configurés avant la démo.")
            )

        profession_specs = [
            ("Agriculteur", "AGRI"),
            ("Enseignant", "ENS"),
            ("Commerçant", "COMMERCE"),
            ("Entrepreneur", "ENT"),
            ("Salarié", "SAL"),
            ("Artisan", "ART"),
            ("Technicien", "TECH"),
            ("Profession libérale", "LIB"),
        ]
        professions = Profession.browse()
        for name, short_code in profession_specs:
            code = f"DEMO-KIIRAAYE-PROF-{short_code}"
            profession = Profession.search([("code", "=", code)], limit=1)
            if not profession:
                profession = Profession.create(
                    {
                        "name": name,
                        "code": code,
                        "sequence": len(professions) + 10,
                        "active": True,
                        "description": "Profession synthétique utilisée uniquement pour les données de démonstration.",
                    }
                )
            professions |= profession

        # Les sections communales sont distribuées sur les vrais villages / quartiers
        # GalsenAPI déjà présents dans le référentiel du Sénégal.
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
        member_section_targets = []
        if not all_demo_sections:
            raise UserError(_("Aucune section de démonstration n'est disponible."))

        for index in range(1, self.member_count + 1):
            section = all_demo_sections[(index - 1) % len(all_demo_sections)]
            member_section_targets.append(section)
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
                    "profession_id": (
                        professions[(index - 1) % len(professions)].id
                        if professions
                        else False
                    ),
                    "active": True,
                    "is_demo_data": True,
                    "section_ids": [(6, 0, [section.id])],
                }
            )

        # Création par lots pour éviter une transaction HTTP trop lourde.
        # On conserve la correspondance membre -> section pour construire
        # immédiatement les bureaux de démonstration.
        created_members = Partisan.browse()
        section_member_map = {}
        batch_size = 80
        for start in range(0, len(member_vals), batch_size):
            batch_members = Partisan.with_context(
                kiiraaye_demo_generation=True
            ).create(member_vals[start:start + batch_size])
            created_members |= batch_members
            for member, section in zip(
                batch_members,
                member_section_targets[start:start + batch_size],
            ):
                section_member_map.setdefault(section.id, []).append(member)
            self.env.cr.commit()

        # Les cinq postes standards sont matérialisés directement dans le
        # bureau pour que la démo soit immédiatement exploitable, sans
        # fabriquer de faux PV.
        standard_positions = positions[:5]
        bureau_vals = []
        bureau_sections = sections
        for section in bureau_sections:
            members = section_member_map.get(section.id, [])
            for position, member in zip(standard_positions, members[:5]):
                bureau_vals.append(
                    {
                        "section_id": section.id,
                        "position_id": position.id,
                        "partisan_id": member.id,
                        "date_debut": fields.Date.context_today(self),
                        "active": True,
                        "sequence": position.sequence,
                    }
                )

        bureau_lines = BureauLine.browse()
        for start in range(0, len(bureau_vals), batch_size):
            bureau_lines |= BureauLine.create(bureau_vals[start:start + batch_size])
            self.env.cr.commit()

        # Organisations de démonstration : une organisation racine et des
        # coordinations rattachées à quelques régions réellement importées.
        organisation_type = OrganisationType.search(
            [("code", "=", "CADRE"), ("active", "=", True)],
            limit=1,
        )
        coordination_type = OrganisationType.search(
            [("code", "=", "COORDINATION"), ("active", "=", True)],
            limit=1,
        )
        demo_organisations = Organisation.browse()
        root_org = Organisation.browse()
        if organisation_type:
            root_org = Organisation.search(
                [("code", "=", "DEMO-KIIRAAYE-ORG-NATIONAL")],
                limit=1,
            )
            if not root_org:
                root_org = Organisation.create(
                    {
                        "name": "Organisation nationale — Démo",
                        "code": "DEMO-KIIRAAYE-ORG-NATIONAL",
                        "type_id": organisation_type.id,
                        "sequence": 1,
                        "active": True,
                        "description": "Organisation synthétique utilisée pour la démonstration du module.",
                    }
                )
            demo_organisations |= root_org
            if created_members:
                root_org.write({"member_ids": [(6, 0, created_members.ids)]})

        if coordination_type:
            for index, region in enumerate(regions[:5], 1):
                code = f"DEMO-KIIRAAYE-ORG-REGION-{index}"
                coord = Organisation.search([("code", "=", code)], limit=1)
                if not coord:
                    coord = Organisation.create(
                        {
                            "name": f"Coordination régionale — {region.name}",
                            "code": code,
                            "type_id": coordination_type.id,
                            "parent_id": root_org.id if root_org else False,
                            "sequence": index + 1,
                            "active": True,
                            "description": "Coordination synthétique utilisée pour la démonstration.",
                        }
                    )
                demo_organisations |= coord
                region_members = created_members.filtered(
                    lambda member, region_id=region.id: member.region_id.id == region_id
                )
                if region_members:
                    coord.write({"member_ids": [(6, 0, region_members.ids)]})

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
                    "du Sénégal, %s coordinations diaspora, %s membres, %s lignes de bureau "
                    "et %s organisations de démonstration générés. Pays diaspora : %s."
                )
                % (
                    len(sections),
                    len(created_diaspora),
                    self.member_count,
                    len(bureau_lines),
                    len(demo_organisations),
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
                "message": _("Les sections, membres, bureaux, organisations et professions de démonstration ont été supprimés. Les données géographiques réelles restent intactes."),
                "type": "success",
                "sticky": False,
            },
        }
