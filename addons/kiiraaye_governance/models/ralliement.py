from odoo import api, fields, models, _
from odoo.exceptions import ValidationError


class KiiraayeRalliement(models.Model):
    _name = "kiiraaye.ralliement"
    _description = "Ralliement Kiiraay"
    _rec_name = "name"
    _order = "name, id"

    name = fields.Char(
        string="Nom",
        required=True,
        index=True,
    )
    code = fields.Char(
        string="Code",
        required=True,
        copy=False,
        index=True,
    )
    type_ralliement = fields.Selection(
        [
            ("parti", "Parti"),
            ("organisation", "Organisation"),
            ("association", "Association"),
            ("mouvement", "Mouvement"),
            ("cooperative", "Coopérative"),
        ],
        string="Type de ralliement",
        required=True,
        default="organisation",
        index=True,
    )
    country_id = fields.Many2one(
        "res.country",
        string="Pays",
        default=lambda self: self.env["res.country"].search([("code", "=", "SN")], limit=1),
        index=True,
        ondelete="restrict",
    )
    date_creation = fields.Date(
        string="Date de création",
        default=fields.Date.context_today,
    )
    description = fields.Text(string="Description")
    active = fields.Boolean(string="Actif", default=True)

    member_ids = fields.Many2many(
        "kiiraaye.partisan",
        "kiiraaye_ralliement_partisan_rel",
        "ralliement_id",
        "partisan_id",
        string="Membres",
    )
    member_count = fields.Integer(
        string="Nombre de membres",
        compute="_compute_member_count",
    )

    _unique_code = models.Constraint(
        "UNIQUE(code)",
        "Le code du ralliement doit être unique.",
    )

    @api.depends("member_ids")
    def _compute_member_count(self):
        for record in self:
            record.member_count = len(record.member_ids)

    @api.constrains("name", "type_ralliement")
    def _check_name(self):
        for record in self:
            if not record.name.strip():
                raise ValidationError(_("Le nom du ralliement ne peut pas être vide."))

    def action_add_members(self):
        self.ensure_one()
        action = self.env.ref(
            "kiiraaye_governance.action_kiiraaye_ralliement_add_members"
        ).read()[0]
        action["context"] = dict(
            self.env.context,
            default_ralliement_id=self.id,
            active_id=self.id,
        )
        return action
