# -*- coding: utf-8 -*-

from odoo import fields, models


class Website(models.Model):
    _inherit = "website"

    def init(self):
        self.env.cr.execute(
            """
            SELECT 1
              FROM information_schema.columns
             WHERE table_name = 'website'
               AND column_name = 'login_theme_show_website_chrome'
            """
        )
        if self.env.cr.fetchone():
            self.env.cr.execute(
                """
                UPDATE website
                   SET login_theme_show_website_chrome = TRUE
                 WHERE login_theme_show_website_chrome IS NULL
                """
            )

    login_theme_id = fields.Many2one(
        "login.theme",
        string="Login Theme",
        help="Published login theme used for this website's login, signup, and password reset pages.",
    )
    login_theme_show_website_chrome = fields.Boolean(
        string="Show Website Header and Footer on Login",
        default=True,
        help="Show the normal website header and footer on login, signup, and password reset pages.",
    )
    login_theme_show_website_header = fields.Boolean(
        string="Show Website Header on Login",
        default=True,
        help="Show the normal website header above login, signup, and password reset pages.",
    )
    login_theme_show_website_footer = fields.Boolean(
        string="Show Website Footer on Login",
        default=True,
        help="Show the normal website footer below login, signup, and password reset pages.",
    )
