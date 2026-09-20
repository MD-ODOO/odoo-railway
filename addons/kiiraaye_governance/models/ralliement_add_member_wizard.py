from odoo import fields, models, _
from odoo.exceptions import UserError


class KiiraayeRalliementAddMembersWizard(models.TransientModel):
    _name = "kiiraaye.ralliement.add.members.wizard"
    _description = "Ajouter des membres à un ralliement Kiiraay"

    ralliement_id = fields.Many2one(
        "kiiraaye.ralliement",
        string="Ralliement",
        required=True,
        readonly=True,
    )
    member_ids = fields.Many2many(
        "kiiraaye.partisan",
        string="Membres à ajouter",
    )

    def action_add(self):
        self.ensure_one()
        if not self.ralliement_id:
            raise UserError(_("Le ralliement est obligatoire."))
        if self.member_ids:
            self.ralliement_id.write({
                "member_ids": [(4, member.id) for member in self.member_ids],
            })
        return {"type": "ir.actions.act_window_close"}
