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
    member_ids = fields.Many2many(
        "kiiraaye.partisan",
        string="Membres à ajouter",
        domain="[('active', '=', True), ('id', 'not in', existing_member_ids)]",
    )
    existing_member_ids = fields.Many2many(
        related="organisation_id.member_ids",
        string="Membres déjà dans l'organisation",
        readonly=True,
    )
    member_id = fields.Many2one(
        "kiiraaye.partisan",
        string="Membre",
        readonly=True,
        copy=False,
    )
    @api.model
    def default_get(self, fields_list):
        vals = super().default_get(fields_list)
        organisation_id = self.env.context.get("default_organisation_id")
        member_ids = self.env.context.get("default_member_ids")
        member_id = self.env.context.get("default_partisan_id") or self.env.context.get("active_id")
        if organisation_id:
            organisation = self.env["kiiraaye.organisation"].browse(organisation_id).exists()
            if organisation:
                vals["organisation_id"] = organisation.id
        if member_ids:
            selected_ids = []
            if isinstance(member_ids, (list, tuple)):
                if all(isinstance(value, int) for value in member_ids):
                    selected_ids = list(member_ids)
                else:
                    for command in member_ids:
                        if isinstance(command, (list, tuple)) and command:
                            if command[0] == 6:
                                selected_ids.extend(command[2] or [])
                            elif command[0] == 4:
                                selected_ids.append(command[1])
            if selected_ids:
                vals["member_ids"] = [(6, 0, list(dict.fromkeys(selected_ids)))]
        elif member_id:
            member = self.env["kiiraaye.partisan"].browse(member_id).exists()
            if member:
                vals["member_ids"] = [(6, 0, [member.id])]
        return vals

    @api.onchange("organisation_id")
    def _onchange_organisation_id(self):
        if not self.organisation_id:
            return {"domain": {"member_ids": [("id", "=", False)]}}
        return {
            "domain": {
                "member_ids": [
                    ("active", "=", True),
                    ("id", "not in", self.organisation_id.member_ids.ids),
                ]
            }
        }

    def action_add(self):
        self.ensure_one()
        if not self.organisation_id:
            raise UserError(_("Sélectionnez une organisation."))

        members = self.member_ids
        if not members and self.member_id:
            members = self.member_id

        if not members:
            raise UserError(_("Sélectionnez au moins un membre."))

        existing = members.filtered(
            lambda member: member in self.organisation_id.member_ids
        )
        if existing:
            raise UserError(
                _(
                    "Les membres suivants appartiennent déjà à cette organisation : %s"
                )
                % ", ".join(existing.mapped("nom_complet"))
            )

        members.write(
            {"organisation_ids": [Command.link(self.organisation_id.id)]}
        )
        return {"type": "ir.actions.act_window_close"}
