from odoo import fields, models


class ResCompany(models.Model):
    _inherit = "res.company"

    appbar_image = fields.Binary(
        string="Apps Menu Footer Image",
        attachment=True,
    )
