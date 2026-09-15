from odoo import fields, models

class ResUsers(models.Model):
    _inherit = "res.users"

    kiiraaye_territoire_id = fields.Many2one(
        "kiiraaye.territoire",
        string="Territoire Kiiraaye",
        help="Territoire de gestion de l'utilisateur."
    )
    kiiraaye_poste_id = fields.Many2one(
        "kiiraaye.position",
        string="Poste Kiiraaye"
    )
