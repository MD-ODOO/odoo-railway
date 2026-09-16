from odoo import fields, models

class KiiraayePosition(models.Model):
    _name = "kiiraaye.position"
    _description = "Poste / fonction Kiiraaye"
    _order = "name"

    name = fields.Char(string="Intitulé", required=True)
    code = fields.Char(string="Code technique", required=True, copy=False)
    active = fields.Boolean(default=True)
    niveau_ids = fields.Selection([
        ("tous", "Tous les niveaux"),
        ("géographique", "Territorial"),
    ], default="géographique", required=True)

    _sql_constraints = [
        ("code_unique", "unique(code)", "Le code du poste doit être unique."),
    ]
