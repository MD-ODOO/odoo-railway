from odoo import api, fields, models, _
from odoo.exceptions import ValidationError


class KiiraayeEffectifStatus(models.Model):
    _name = "kiiraaye.effectif.status"
    _description = "Statut d'effectif Kiiraaye"
    _rec_name = "name"
    _order = "sequence, min_members, name"

    name = fields.Char(
        string="Statut",
        required=True,
        index=True,
    )
    code = fields.Char(
        string="Code",
        required=True,
        copy=False,
        index=True,
    )
    min_members = fields.Integer(
        string="Minimum de membres",
        required=True,
        default=0,
    )
    max_members = fields.Integer(
        string="Maximum de membres",
        help="Laisser vide pour une borne supérieure illimitée.",
    )
    sequence = fields.Integer(
        string="Séquence",
        default=10,
    )
    color = fields.Integer(
        string="Couleur",
        default=1,
    )
    description = fields.Text(
        string="Description",
    )
    active = fields.Boolean(
        string="Actif",
        default=True,
    )

    _unique_code = models.Constraint(
        "UNIQUE(code)",
        "Le code du statut d'effectif doit être unique.",
    )

    @api.constrains("min_members", "max_members")
    def _check_range(self):
        for record in self:
            if record.min_members < 0:
                raise ValidationError(_("Le minimum de membres ne peut pas être négatif."))
            if record.max_members and record.max_members < record.min_members:
                raise ValidationError(
                    _("Le maximum de membres doit être supérieur ou égal au minimum.")
                )

    @api.model
    def get_for_count(self, count):
        count = max(0, int(count or 0))
        return self.search(
            [
                ("active", "=", True),
                ("min_members", "<=", count),
                "|",
                ("max_members", "=", False),
                ("max_members", ">=", count),
            ],
            order="sequence, min_members desc, id",
            limit=1,
        )
