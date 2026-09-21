from odoo import fields, models


class ResCompany(models.Model):
    _inherit = "res.company"

    appbar_image = fields.Binary(
        string="Apps Menu Footer Image",
        attachment=True,
    )

    appbar_background_color = fields.Char(
        string="AppsBar Background Color",
        default="#172033",
        help="Couleur libre utilisée comme couleur de fond principale de la barre des applications.",
    )
