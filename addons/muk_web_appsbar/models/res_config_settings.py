from odoo import fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = "res.config.settings"

    appbar_image = fields.Binary(
        related="company_id.appbar_image",
        readonly=False,
    )

    appbar_background_color = fields.Char(
        related="company_id.appbar_background_color",
        readonly=False,
    )
