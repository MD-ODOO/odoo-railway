from odoo import fields, models


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

    def _compute_kiiraaye_scope(self):
        Section = self.env["kiiraaye.section"].sudo()
        Partisan = self.env["kiiraaye.partisan"].sudo()
        for user in self:
            partisan = Partisan.search(
                [("user_id", "=", user.id)],
                limit=1,
            )
            sections = Section.search(
                [
                    ("cordonnateur_id.user_id", "=", user.id),
                    ("active", "=", True),
                    ("state", "=", "ouverte"),
                ]
            )
            user.kiiraaye_partisan_id = partisan
            user.kiiraaye_coordinator_section_ids = sections
            user.kiiraaye_coordinator_region_ids = sections.filtered(
                lambda s: s.type_section == "regionale"
            ).mapped("region_id")
            user.kiiraaye_coordinator_departement_ids = sections.filtered(
                lambda s: s.type_section == "departementale"
            ).mapped("departement_id")
            communal = sections.filtered(lambda s: s.type_section == "communale")
            user.kiiraaye_coordinator_commune_ids = communal.mapped("commune_id")
            user.kiiraaye_coordinator_quartier_ids = communal.mapped("quartier_id")
