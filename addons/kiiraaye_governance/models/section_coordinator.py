from odoo import api, fields, models, _, Command
from odoo.exceptions import ValidationError


class KiiraayeSectionCoordinator(models.Model):
    _inherit = "kiiraaye.section"

    cordonnateur_id = fields.Many2one(
        "kiiraaye.partisan",
        string="Coordonnateur",
        ondelete="restrict",
        index=True,
        help="Membre unique du bureau habilité à créer des membres dans la zone de la section.",
    )

    @api.constrains("cordonnateur_id", "membre_ids", "state", "active")
    def _check_cordonnateur(self):
        for record in self:
            if not record.cordonnateur_id:
                continue
            if record.cordonnateur_id not in record.membre_ids:
                raise ValidationError(
                    _("Le coordonnateur doit obligatoirement être membre de la section / coordination.")
                )
            if not record.cordonnateur_id.user_id:
                raise ValidationError(
                    _("Le coordonnateur doit être lié à un utilisateur Odoo avant d'être habilité.")
                )

    @api.model
    def _sync_coordinator_access(self):
        group = self.env.ref(
            "kiiraaye_governance.group_kiiraaye_coordinator",
            raise_if_not_found=False,
        )
        if not group:
            return

        sections = self.env["kiiraaye.section"].sudo().search([
            ("cordonnateur_id", "!=", False),
            ("cordonnateur_id.user_id", "!=", False),
            ("active", "=", True),
            ("state", "=", "ouverte"),
        ])
        active_coordinators = sections.mapped("cordonnateur_id.user_id")
        current_group_users = group.user_ids

        for user in active_coordinators - current_group_users:
            user.write({"group_ids": [Command.link(group.id)]})
        for user in current_group_users - active_coordinators:
            user.write({"group_ids": [Command.unlink(group.id)]})

        coord_position = self.env["kiiraaye.position"].sudo().search(
            [("code", "=", "COORD")], limit=1
        )
        if not coord_position:
            return
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
                line.write({
                    "partisan_id": section.cordonnateur_id.id,
                    "active": True,
                    "date_debut": section.date_creation,
                })
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
