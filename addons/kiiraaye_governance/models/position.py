from odoo import fields, models


class KiiraayePosition(models.Model):
    _name = "kiiraaye.position"
    _description = "Poste de bureau Kiiraaye"
    _rec_name = "name"
    _order = "sequence, name"

    name = fields.Char(string="Intitulé du poste", required=True)
    code = fields.Char(string="Code", required=True)
    sequence = fields.Integer(string="Séquence", default=10)
    active = fields.Boolean(string="Actif", default=True)

    _unique_code = models.Constraint(
        "UNIQUE(code)",
        "Le code du poste doit être unique.",
    )
