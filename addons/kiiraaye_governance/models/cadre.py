from odoo import api, fields, models, _


class KiiraayeCadre(models.Model):
    _name = "kiiraaye.cadre"
    _description = "Ancienne organisation Kiiraaye"
    _rec_name = "name"
    _order = "sequence, name"

    name = fields.Char(
        string="Ancienne organisation",
        required=True,
        index=True,
    )
    code = fields.Char(
        string="Code",
        required=True,
        copy=False,
        index=True,
    )
    sequence = fields.Integer(
        string="Séquence",
        default=10,
    )
    color = fields.Integer(
        string="Couleur",
        default=1,
        help="Couleur utilisée pour l'identification visuelle de l'ancienne organisation.",
    )
    description = fields.Text(
        string="Description",
    )
    active = fields.Boolean(
        string="Actif",
        default=True,
    )
    member_ids = fields.One2many(
        "kiiraaye.partisan",
        "cadre_id",
        string="Membres",
    )
    member_count = fields.Integer(
        string="Nombre de membres",
        compute="_compute_member_count",
    )

    _unique_code = models.Constraint(
        "UNIQUE(code)",
        "Le code de l'ancienne organisation doit être unique.",
    )

    @api.depends("member_ids")
    def _compute_member_count(self):
        for record in self:
            record.member_count = len(record.member_ids)
