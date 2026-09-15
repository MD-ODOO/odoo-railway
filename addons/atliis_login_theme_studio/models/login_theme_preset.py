# -*- coding: utf-8 -*-

from odoo import fields, models


class LoginThemePreset(models.Model):
    """Compatibility model for uninstalling older builds that shipped presets."""

    _name = "login.theme.preset"
    _description = "Login Theme Preset"
    _order = "sequence, name, id"

    name = fields.Char(required=True)
    description = fields.Text()
    preview_image = fields.Image(max_width=1024, max_height=768)
    category = fields.Selection(
        [
            ("corporate", "Corporate"),
            ("modern", "Modern"),
            ("minimal", "Minimal"),
            ("dark", "Dark"),
            ("industry", "Industry"),
        ],
        default="corporate",
        required=True,
    )
    configuration_json = fields.Text(default="{}")
    active = fields.Boolean(default=True)
    sequence = fields.Integer(default=10)
