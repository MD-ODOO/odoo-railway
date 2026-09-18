from odoo import models


class KiiraayeProfession(models.Model):
    _name = "kiiraaye.profession"
    _description = "Profession d'un membre Kiiraaye"
    _rec_name = "name"
    _order = "sequence, name"

    name = models.Char(
        string="Profession",
        required=True,
        index=True,
    )
    code = models.Char(
        string="Code",
        required=True,
        copy=False,
        index=True,
    )
    sequence = models.Integer(
        string="Séquence",
        default=10,
    )
    active = models.Boolean(
        string="Actif",
        default=True,
    )
    description = models.Text(
        string="Description",
    )

    _unique_code = models.Constraint(
        "UNIQUE(code)",
        "Le code de la profession doit être unique.",
    )
