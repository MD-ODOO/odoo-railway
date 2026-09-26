from odoo import api, fields, models


class ResUsers(models.Model):
    _inherit = "res.users"

    kiiraaye_partisan_id = fields.Many2one(
        "kiiraaye.partisan",
        string="Membre Kiiraaye",
        compute="_compute_kiiraaye_scope",
        compute_sudo=True,
    )
    kiiraaye_coordinator_section_ids = fields.Many2many(
        "kiiraaye.section",
        string="Sections coordonnées Kiiraaye",
        compute="_compute_kiiraaye_scope",
        compute_sudo=True,
    )
    kiiraaye_coordinator_region_ids = fields.Many2many(
        "kiiraaye.geographie",
        string="Régions autorisées Kiiraaye",
        compute="_compute_kiiraaye_scope",
        compute_sudo=True,
    )
    kiiraaye_coordinator_departement_ids = fields.Many2many(
        "kiiraaye.geographie",
        string="Départements autorisés Kiiraaye",
        compute="_compute_kiiraaye_scope",
        compute_sudo=True,
    )
    kiiraaye_coordinator_commune_ids = fields.Many2many(
        "kiiraaye.geographie",
        string="Communes autorisées Kiiraaye",
        compute="_compute_kiiraaye_scope",
        compute_sudo=True,
    )
    kiiraaye_coordinator_quartier_ids = fields.Many2many(
        "kiiraaye.geographie",
        string="Quartiers autorisés Kiiraaye",
        compute="_compute_kiiraaye_scope",
        compute_sudo=True,
    )

    @api.depends("id", "groups_id")
    def _compute_kiiraaye_scope(self):
        Section = self.env["kiiraaye.section"].sudo()
        Partisan = self.env["kiiraaye.partisan"].sudo()
        Geography = self.env["kiiraaye.geographie"].sudo()

        for user in self:
            partisan = Partisan.search([("user_id", "=", user.id)], limit=1)
            sections = Section.search([
                ("cordonnateur_id.user_id", "=", user.id),
                ("active", "=", True),
                ("state", "=", "ouverte"),
            ])

            regions = sections.filtered(
                lambda s: s.type_section == "regionale" and s.region_id
            ).mapped("region_id")
            departments = sections.filtered(
                lambda s: s.type_section == "departementale" and s.departement_id
            ).mapped("departement_id")
            communes = sections.filtered(
                lambda s: s.type_section == "communale" and s.commune_id
            ).mapped("commune_id")
            quartiers = sections.filtered(
                lambda s: s.type_section == "communale" and s.quartier_id
            ).mapped("quartier_id")

            # Héritage hiérarchique : régional -> département -> commune -> quartier.
            if regions:
                departments |= Geography.search([
                    ("niveau", "=", "niveau2"),
                    ("id", "child_of", regions.ids),
                    ("active", "=", True),
                ])
            if departments:
                communes |= Geography.search([
                    ("niveau", "=", "niveau3"),
                    ("id", "child_of", departments.ids),
                    ("active", "=", True),
                ])
            if communes:
                quartiers |= Geography.search([
                    ("niveau", "=", "niveau5"),
                    ("id", "child_of", communes.ids),
                    ("active", "=", True),
                ])

            user.kiiraaye_partisan_id = partisan
            user.kiiraaye_coordinator_section_ids = sections
            user.kiiraaye_coordinator_region_ids = regions
            user.kiiraaye_coordinator_departement_ids = departments
            user.kiiraaye_coordinator_commune_ids = communes
            user.kiiraaye_coordinator_quartier_ids = quartiers
