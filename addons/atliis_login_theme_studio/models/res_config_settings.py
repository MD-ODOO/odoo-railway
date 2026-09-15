# -*- coding: utf-8 -*-

from odoo import api, fields, models, _


LOGIN_THEME_SETTINGS_FIELD_HELP = {
    "login_theme_default_theme_id": "Login theme used for the selected website's authentication pages.",
    "login_theme_show_website_chrome": "Show the selected website's normal header and footer on authentication pages.",
    "login_theme_fallback_mode": "Choose what Odoo should render if no published login theme can be applied.",
}


class ResConfigSettings(models.TransientModel):
    _inherit = "res.config.settings"

    login_theme_default_theme_id = fields.Many2one(
        "login.theme",
        string="Login Theme",
        related="website_id.login_theme_id",
        readonly=False,
    )
    login_theme_show_website_header = fields.Boolean(
        string="Show Website Header",
        related="website_id.login_theme_show_website_header",
        readonly=False,
    )
    login_theme_show_website_footer = fields.Boolean(
        string="Show Website Footer",
        related="website_id.login_theme_show_website_footer",
        readonly=False,
    )
    login_theme_show_website_chrome = fields.Boolean(
        string="Show Website Header and Footer",
        related="website_id.login_theme_show_website_chrome",
        readonly=False,
    )
    force_native_login = fields.Boolean(
        string="Force Native Login",
        config_parameter="atliis_login_theme_studio.force_native_login",
    )
    enable_domain_theme_resolution = fields.Boolean(
        string="Enable Domain Theme Resolution",
        default=True,
        config_parameter="atliis_login_theme_studio.enable_domain_theme_resolution",
    )
    enable_theme_scheduling = fields.Boolean(
        string="Enable Theme Scheduling",
        default=True,
        config_parameter="atliis_login_theme_studio.enable_theme_scheduling",
    )
    login_theme_fallback_mode = fields.Selection(
        [
            ("configured", "Configured Default Theme"),
            ("native", "Native Odoo Login"),
        ],
        string="Fallback Mode",
        default="configured",
        config_parameter="atliis_login_theme_studio.fallback_mode",
    )

    @api.model
    def fields_get(self, allfields=None, attributes=None):
        fields_data = super().fields_get(allfields=allfields, attributes=attributes)
        for field_name, help_text in LOGIN_THEME_SETTINGS_FIELD_HELP.items():
            if field_name in fields_data:
                fields_data[field_name]["help"] = _(help_text)
        return fields_data
