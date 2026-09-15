from odoo import fields, models


class KiiraayeSettings(models.TransientModel):
    _name = "kiiraaye.settings"
    _description = "Configuration Kiiraaye"

    company_id = fields.Many2one(
        "res.company", required=True,
        default=lambda self: self.env.company
    )
    card_title = fields.Char(
        string="Titre de la carte", default="CARTE DE MEMBRE"
    )
    card_subtitle = fields.Char(
        string="Sous-titre", default="KIIRAAYE"
    )
    card_primary_color = fields.Char(
        string="Couleur principale", default="#1D4ED8"
    )
    card_secondary_color = fields.Char(
        string="Couleur secondaire", default="#0F172A"
    )
