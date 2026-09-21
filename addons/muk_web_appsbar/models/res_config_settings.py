from odoo import fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = "res.config.settings"

    appbar_image = fields.Binary(
        related="company_id.appbar_image",
        readonly=False,
    )
