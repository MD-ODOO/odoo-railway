from odoo import api, fields, models, _
from odoo.exceptions import ValidationError


class KiiraayeSectionCoordinator(models.Model):
    _inherit = "kiiraaye.section"

    cordonnateur_id = fields.Many2one(
        "kiiraaye.partisan",
        string="Coordonnateur",
        ondelete="restrict",
        index=True,
        help="Membre unique désigné comme coordonnateur de la section / coordination.",
    )

    @api.constrains("cordonnateur_id", "membre_ids", "state", "active")
    def _check_cordonnateur(self):
        for record in self:
            if not record.cordonnateur_id:
                continue
            if record.cordonnateur_id not in record.membre_ids:
                raise ValidationError(_("Le coordonnateur doit obligatoirement être membre de la section / coordination."))
            if not record.cordonnateur_id.user_id:
                raise ValidationError(_("Le coordonnateur doit être lié à un utilisateur Odoo avant d'être habilité."))
            if not record.cordonnateur_id.user_id.kiiraaye_role:
                raise ValidationError(_("Le membre désigné comme coordonnateur doit avoir une fonction Kiiraaye configurée sur son utilisateur Odoo."))

    @api.model
    def _sync_coordinator_access(self):
        # Le périmètre de sécurité est maintenant piloté par la fonction
        # Kiiraaye du compte utilisateur. Ici, on synchronise uniquement
        # la ligne COORD du bureau avec le coordonnateur de la section.
        coord_position = self.env["kiiraaye.position"].sudo().search(
            [("code", "=", "COORD")], limit=1
        )
        if not coord_position:
            return
        sections = self.env["kiiraaye.section"].sudo().search([
            ("cordonnateur_id", "!=", False),
            ("cordonnateur_id.user_id", "!=", False),
            ("active", "=", True),
            ("state", "=", "ouverte"),
        ])
        BureauLine = self.env["kiiraaye.bureau.ligne"].sudo()
        for section in sections:
            line = BureauLine.search(
                [("section_id", "=", section.id), ("position_id", "=", coord_position.id)],
                limit=1,
            )
            values = {
                "section_id": section.id,
                "position_id": coord_position.id,
                "partisan_id": section.cordonnateur_id.id,
                "date_debut": section.date_creation,
                "active": True,
            }
            if line:
                line.write(values)
            else:
                BureauLine.create(values)

    @api.model_create_multi
    def create(self, vals_list):
        records = super().create(vals_list)
        self._sync_coordinator_access()
        return records

    def write(self, vals):
        result = super().write(vals)
        if {"cordonnateur_id", "state", "active", "membre_ids"}.intersection(vals):
            self._sync_coordinator_access()
        return result

    def unlink(self):
        result = super().unlink()
        self._sync_coordinator_access()
        return result
