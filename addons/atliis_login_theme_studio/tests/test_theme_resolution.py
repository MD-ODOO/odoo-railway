# -*- coding: utf-8 -*-

from odoo.tests.common import TransactionCase, tagged


@tagged("post_install", "-at_install")
class TestLoginThemeResolution(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.Theme = cls.env["login.theme"]
        cls.Config = cls.env["ir.config_parameter"].sudo()

    def setUp(self):
        super().setUp()
        self.Config.set_param("atliis_login_theme_studio.force_native_login", "")
        self.Config.set_param("atliis_login_theme_studio.enable_domain_theme_resolution", "True")
        self.Config.set_param("atliis_login_theme_studio.enable_theme_scheduling", "True")
        self.Config.set_param("atliis_login_theme_studio.fallback_mode", "configured")
        self.Theme.search([]).write({"published": False, "is_default": False})

    def test_domain_theme_takes_priority_over_global_default(self):
        global_theme = self.Theme.create(
            {
                "name": "Global Default",
                "published": True,
                "is_default": True,
                "sequence": 99,
            }
        )
        domain_theme = self.Theme.create(
            {
                "name": "Domain Theme",
                "published": True,
                "domain_name": "login.example.com",
                "sequence": 1,
            }
        )
        resolved = self.Theme._get_theme_for_request(domain_name="https://login.example.com/web/login")
        self.assertEqual(resolved, domain_theme)
        self.assertGreater(domain_theme.resolution_priority, global_theme.resolution_priority)

    def test_configured_fallback_is_used_when_no_scoped_theme_matches(self):
        theme = self.Theme.create(
            {
                "name": "Configured Fallback",
                "published": True,
                "sequence": 50,
            }
        )
        self.Config.set_param("atliis_login_theme_studio.default_login_theme_id", str(theme.id))
        resolved = self.Theme._get_theme_for_request(domain_name="missing.example.com", company=False)
        self.assertEqual(resolved, theme)

    def test_native_fallback_skips_configured_default(self):
        theme = self.Theme.create(
            {
                "name": "Skipped Fallback",
                "published": True,
                "sequence": 50,
            }
        )
        self.Config.set_param("atliis_login_theme_studio.default_login_theme_id", str(theme.id))
        self.Config.set_param("atliis_login_theme_studio.fallback_mode", "native")
        resolved = self.Theme._get_theme_for_request(domain_name="missing.example.com", company=False)
        self.assertFalse(resolved)

    def test_force_native_login_returns_empty_public_payload(self):
        self.Config.set_param("atliis_login_theme_studio.force_native_login", "True")
        values = self.Theme._get_public_theme_values()
        self.assertEqual(values, {})
