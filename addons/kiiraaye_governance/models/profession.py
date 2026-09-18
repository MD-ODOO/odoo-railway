from odoo import fields, models


class KiiraayeProfession(models.Model):
    _name = "kiiraaye.profession"
    _description = "Profession d'un membre Kiiraaye"
    _rec_name = "name"
    _order = "sequence, name"

    name = fields.Char(
        string="Profession",
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
    active = fields.Boolean(
        string="Actif",
        default=True,
    )
    description = fields.Text(
        string="Description",
    )

    _unique_code = models.Constraint(
        "UNIQUE(code)",
        "Le code de la profession doit être unique.",
    )
