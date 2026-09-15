# -*- coding: utf-8 -*-

{
    "name": "Login Theme Studio",
    "summary": "Customise Odoo login, signup and password reset pages",
    "description": """
Login Theme Studio lets Odoo administrators brand login, signup, and password
reset pages from Website settings without replacing Odoo authentication.

Features
--------
- Per-website login theme selection from Website settings
- Native Odoo login fallback when no website theme is selected
- No-code editor for logo, colours, typography, layout, background, form text,
  footer links, and announcements
- Uploaded and external background image support
- Desktop and tablet preview before publishing
- Native colour picker widget for visible colour fields
- Hover help for visible settings and theme fields
- Manager-only access to login theme configuration
""",
    "version": "19.0.1.0.0",
    "category": "Website",
    "author": "Atliis 360",
    "maintainer": "Atliis 360",
    "website": "https://www.atliis.com",
    "support": "helpdesk@atliis.com",
    "live_test_url": "https://demov19.atliis.com/web/login?utm_source=odoo_apps&utm_medium=live_preview&utm_campaign=atliis_login_theme_studio",
    "price": 0.0,
    "currency": "USD",
    "license": "OPL-1",
    "depends": [
        "base",
        "web",
        "website",
        "auth_signup",
    ],
    "data": [
        "security/login_theme_security.xml",
        "security/ir.model.access.csv",
        "views/login_theme_views.xml",
        "views/res_config_settings_views.xml",
        "views/authentication_templates.xml",
        "views/login_preview_templates.xml",
        "views/menus.xml",
    ],
    "assets": {
        "web.assets_backend": [
            "atliis_login_theme_studio/static/src/js/login_theme_color_field.js",
            "atliis_login_theme_studio/static/src/xml/login_theme_color_field.xml",
            "atliis_login_theme_studio/static/src/scss/login_theme_color_field.scss",
        ],
        "web.assets_frontend": [
            "atliis_login_theme_studio/static/src/scss/authentication.scss",
            "atliis_login_theme_studio/static/src/js/authentication.js",
        ],
    },
    "images": [
        "static/description/banner.jpg",
        "static/description/icon.png",
    ],
    "installable": True,
    "application": True,
    "auto_install": False,
}
