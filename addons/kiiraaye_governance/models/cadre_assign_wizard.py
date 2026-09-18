from odoo import api, fields, models, _
from odoo.exceptions import UserError


class KiiraayeCadreAssignWizard(models.TransientModel):
    _name = "kiiraaye.cadre.assign.wizard"
    _description = "Affectation d'un membre à un cadre Kiiraaye"

    partisan_id = fields.Many2one(
        "kiiraaye.partisan",
        string="Membre",
        required=True,
        readonly=True,
    )
    current_cadre_id = fields.Many2one(
        related="partisan_id.cadre_id",
        string="Cadre actuel",
        readonly=True,
    )
    cadre_id = fields.Many2one(
        "kiiraaye.cadre",
        string="Nouveau cadre",
        required=True,
        domain="[('active', '=', True)]",
    )

    @api.model
    def default_get(self, fields_list):
        vals = super().default_get(fields_list)
        partisan_id = self.env.context.get("default_partisan_id") or self.env.context.get("active_id")
        if partisan_id:
            partisan = self.env["kiiraaye.partisan"].browse(partisan_id).exists()
            if partisan:
                vals["partisan_id"] = partisan.id
        return vals

    def action_assign(self):
        self.ensure_one()
        if not self.partisan_id:
            raise UserError(_("Aucun membre n'a été sélectionné."))
        if not self.cadre_id:
            raise UserError(_("Sélectionnez un cadre."))

        self.partisan_id.write({"cadre_id": self.cadre_id.id})
        return {"type": "ir.actions.act_window_close"}
