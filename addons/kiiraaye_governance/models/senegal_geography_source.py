# -*- coding: utf-8 -*-
from odoo import fields, models


class ResCountrySenegalGeographySource(models.Model):
    _inherit = "res.country"

    kiiraaye_geo_source = fields.Selection(
        selection_add=[
            ("galsenapi", "GalsenAPI (Sénégal)"),
        ],
        ondelete={
            "galsenapi": "set default",
        },
    )
