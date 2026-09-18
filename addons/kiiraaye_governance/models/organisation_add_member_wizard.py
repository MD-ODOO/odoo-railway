from odoo import api, fields, models, Command, _
from odoo.exceptions import UserError


class KiiraayeOrganisationAddMemberWizard(models.TransientModel):
    _name = "kiiraaye.organisation.add.member.wizard"
    _description = "Ajouter un membre à une organisation Kiiraaye"

    organisation_id = fields.Many2one(
        "kiiraaye.organisation",
        string="Organisation",
        required=True,
        readonly=True,
    )
    member_id = fields.Many2one(
        "kiiraaye.partisan",
        string="Membre",
        required=True,
        domain="[('active', '=', True)]",
    )
    current_organisation_ids = fields.Many2many(
        related="member_id.organisation_ids",
        string="Organisations actuelles",
        readonly=True,
    )

    @api.model
    def default_get(self, fields_list):
        vals = super().default_get(fields_list)
        organisation_id = (
            self.env.context.get("default_organisation_id")
            or self.env.context.get("active_id")
        )
        if organisation_id:
            organisation = self.env["kiiraaye.organisation"].browse(organisation_id).exists()
            if organisation:
                vals["organisation_id"] = organisation.id
        return vals

    @api.onchange("organisation_id")
    def _onchange_organisation_id(self):
        if not self.organisation_id:
            return {"domain": {"member_id": [("id", "=", False)]}}
        return {
            "domain": {
                "member_id": [
                    ("active", "=", True),
                    ("id", "not in", self.organisation_id.member_ids.ids),
                ]
            }
        }

    def action_add(self):
        self.ensure_one()
        if not self.organisation_id:
            raise UserError(_("Sélectionnez une organisation."))
        if not self.member_id:
            raise UserError(_("Sélectionnez un membre."))
        if self.member_id in self.organisation_id.member_ids:
            raise UserError(_("Ce membre appartient déjà à cette organisation."))

        self.member_id.write(
            {"organisation_ids": [Command.link(self.organisation_id.id)]}
        )
        return {"type": "ir.actions.act_window_close"}
