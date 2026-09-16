from odoo import fields, models

class ResUsers(models.Model):
    _inherit = "res.users"

    kiiraaye_geographie_id = fields.Many2one(
        "kiiraaye.geographie",
        string="Zone géographique Kiiraaye",
        help="Zone géographique de gestion de l'utilisateur."
    )
    kiiraaye_poste_id = fields.Many2one(
        "kiiraaye.position",
        string="Poste Kiiraaye"
    )
