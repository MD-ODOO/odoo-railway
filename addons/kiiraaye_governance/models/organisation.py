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
    child_ids = fields.One2many(
        "kiiraaye.organisation",
        "parent_id",
        string="Organisations enfants",
    )
    niveau = fields.Integer(
        related="type_id.niveau",
        string="Niveau",
        store=True,
        readonly=True,
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
    legacy_cadre_id = fields.Many2one(
        "kiiraaye.cadre",
        string="Cadre historique",
        ondelete="set null",
        copy=False,
        index=True,
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
    member_status_id = fields.Many2one(
        "kiiraaye.effectif.status",
        string="Statut d'effectif",
        compute="_compute_member_status",
    )

    _unique_code = models.Constraint(
        "UNIQUE(code)",
        "Le code de l'organisation doit être unique.",
    )

    @api.depends("member_ids")
    def _compute_member_count(self):
        for record in self:
            record.member_count = len(record.member_ids)

    @api.depends("member_count")
    def _compute_member_status(self):
        Status = self.env["kiiraaye.effectif.status"]
        for record in self:
            record.member_status_id = Status.get_for_count(record.member_count)

    @api.constrains("parent_id")
    def _check_parent(self):
        for record in self:
            if not record.parent_id:
                continue
            if record.parent_id == record:
                raise ValidationError(_("Une organisation ne peut pas être sa propre organisation parente."))
            current = record.parent_id
            while current:
                if current == record:
                    raise ValidationError(_("La hiérarchie des organisations contient une boucle."))
                current = current.parent_id

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
