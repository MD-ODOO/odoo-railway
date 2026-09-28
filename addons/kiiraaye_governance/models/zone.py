from odoo import api, fields, models, _
from odoo.exceptions import ValidationError


class KiiraayeZone(models.Model):
    _name = "kiiraaye.zone"
    _description = "Zone Kiiraaye"
    _rec_name = "name"
    _order = "name, id"

    name = fields.Char(string="Nom de la zone", required=True, index=True)
    reference = fields.Char(string="Référence", required=True, copy=False, readonly=True,
                            default=lambda self: self.env["ir.sequence"].next_by_code("kiiraaye.zone") or "Nouveau")
    country_id = fields.Many2one("res.country", string="Pays", required=True,
                                 default=lambda self: self.env["res.country"].search([("code", "=", "SN")], limit=1),
                                 ondelete="restrict")
    commune_id = fields.Many2one(
        "kiiraaye.geographie", string="Commune", required=True, ondelete="restrict",
        domain="[('country_id', '=', country_id), ('niveau', '=', 'niveau3'), ('active', '=', True)]",
    )
    quartier_ids = fields.Many2many(
        "kiiraaye.geographie", "kiiraaye_zone_quartier_rel", "zone_id", "quartier_id",
        string="Quartiers", domain="[('country_id', '=', country_id), ('niveau', '=', 'niveau5'), ('id', 'child_of', commune_id), ('active', '=', True)]",
    )
    section_ids = fields.Many2many(
        "kiiraaye.section", string="Sections de la zone", compute="_compute_section_ids",
    )
    responsable_user_id = fields.Many2one(
        "res.users", string="Responsable de zone", ondelete="restrict",
        domain="[('kiiraaye_role', '=', 'zone')]",
    )
    active = fields.Boolean(string="Actif", default=True)

    _unique_reference = models.Constraint("UNIQUE(reference)", "La référence de la zone doit être unique.")
    _unique_name_commune = models.Constraint(
        "UNIQUE(name, commune_id)", "Une zone portant ce nom existe déjà dans cette commune."
    )

    @api.depends("commune_id", "quartier_ids")
    def _compute_section_ids(self):
        Section = self.env["kiiraaye.section"].sudo()
        for zone in self:
            domain = [
                ("active", "=", True),
                ("type_section", "=", "communale"),
                ("commune_id", "=", zone.commune_id.id),
            ]
            if zone.quartier_ids:
                domain.append(("quartier_id", "in", zone.quartier_ids.ids))
            else:
                domain.append(("id", "=", False))
            zone.section_ids = Section.search(domain)

    @api.onchange("commune_id")
    def _onchange_commune_id(self):
        if self.quartier_ids:
            self.quartier_ids = self.quartier_ids.filtered(lambda q: self._quartier_belongs_to_commune(q, self.commune_id))

    @api.onchange("quartier_ids")
    def _onchange_quartier_ids(self):
        if self.commune_id:
            invalid = self.quartier_ids.filtered(lambda q: not self._quartier_belongs_to_commune(q, self.commune_id))
            if invalid:
                self.quartier_ids -= invalid

    @staticmethod
    def _quartier_belongs_to_commune(quartier, commune):
        if not quartier or not commune or quartier.niveau != "niveau5":
            return False
        current = quartier
        while current:
            if current.parent_id == commune:
                return True
            current = current.parent_id
        return False

    @api.constrains("country_id", "commune_id", "quartier_ids", "responsable_user_id")
    def _check_zone(self):
        for zone in self:
            if zone.commune_id and (zone.commune_id.country_id != zone.country_id or zone.commune_id.niveau != "niveau3"):
                raise ValidationError(_("La commune de la zone est invalide."))
            invalid = zone.quartier_ids.filtered(lambda q: not self._quartier_belongs_to_commune(q, zone.commune_id))
            if invalid:
                raise ValidationError(_("Tous les quartiers d'une zone doivent appartenir à sa commune."))
            if zone.responsable_user_id and zone.responsable_user_id.kiiraaye_role != "zone":
                raise ValidationError(_("Le responsable de zone doit avoir le rôle Responsable de zone."))

    @api.model_create_multi
    def create(self, vals_list):
        records = super().create(vals_list)
        records._sync_responsable_users()
        return records

    def write(self, vals):
        result = super().write(vals)
        if "responsable_user_id" in vals:
            self._sync_responsable_users()
        return result

    def _sync_responsable_users(self):
        for zone in self:
            if zone.responsable_user_id and zone.responsable_user_id.kiiraaye_zone_id != zone:
                zone.responsable_user_id.with_context(kiiraaye_skip_zone_sync=True).write({"kiiraaye_zone_id": zone.id})
