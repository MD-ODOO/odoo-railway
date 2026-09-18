from odoo import api, fields, models, _
from odoo.exceptions import ValidationError


class KiiraayeOrganisation(models.Model):
    _name = "kiiraaye.organisation"
    _description = "Organisation Kiiraaye"
    _rec_name = "name"
    _order = "sequence, name"

    name = fields.Char(
        string="Organisation",
        required=True,
        index=True,
    )
    code = fields.Char(
        string="Code",
        required=True,
        copy=False,
        index=True,
    )
    type_id = fields.Many2one(
        "kiiraaye.organisation.type",
        string="Type / niveau",
        required=True,
        ondelete="restrict",
        index=True,
    )
    parent_id = fields.Many2one(
        "kiiraaye.organisation",
        string="Organisation parente",
        ondelete="restrict",
        index=True,
    )
    sequence = fields.Integer(
        string="Séquence",
        default=10,
    )
    color = fields.Integer(
        string="Couleur",
        default=1,
        help="Couleur utilisée pour l'identification visuelle de l'organisation.",
    )
    date_creation = fields.Date(
        string="Date de création",
        default=fields.Date.context_today,
    )
    description = fields.Text(
        string="Description",
    )
    active = fields.Boolean(
        string="Actif",
        default=True,
    )
    member_ids = fields.Many2many(
        "kiiraaye.partisan",
        "kiiraaye_organisation_partisan_rel",
        "organisation_id",
        "partisan_id",
        string="Membres",
    )
    member_count = fields.Integer(
        string="Nombre de membres",
        compute="_compute_member_count",
    )

    _unique_code = models.Constraint(
        "UNIQUE(code)",
        "Le code de l'organisation doit être unique.",
    )

    @api.depends("member_ids")
    def _compute_member_count(self):
        for record in self:
            record.member_count = len(record.member_ids)

    @api.constrains("parent_id")
    def _check_parent(self):
        for record in self:
            if not record.parent_id:
                continue
            if record.parent_id == record:
                raise ValidationError(_("Une organisation ne peut pas être sa propre organisation parente."))
            if record.parent_id in record.child_of(record):
                raise ValidationError(_("La hiérarchie des organisations contient une boucle."))

    def action_add_member(self):
        self.ensure_one()
        action = self.env.ref(
            "kiiraaye_governance.action_kiiraaye_organisation_add_member_wizard"
        ).read()[0]
        action["context"] = dict(
            self.env.context,
            default_organisation_id=self.id,
            active_id=self.id,
        )
        return action
