# -*- coding: utf-8 -*-

from odoo.exceptions import AccessError
from odoo.tests.common import TransactionCase, new_test_user, tagged


@tagged("post_install", "-at_install")
class TestLoginThemeSecurity(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.Theme = cls.env["login.theme"]
        cls.viewer = new_test_user(
            cls.env,
            login="login_theme_viewer",
            groups="base.group_user,atliis_login_theme_studio.group_login_theme_viewer",
        )
        cls.manager = new_test_user(
            cls.env,
            login="login_theme_manager",
            groups="base.group_user,atliis_login_theme_studio.group_login_theme_manager",
        )

    def test_viewer_cannot_access_theme(self):
        theme = self.Theme.create({"name": "Read Only Theme"})
        viewer_theme = theme.with_user(self.viewer)
        with self.assertRaises(AccessError):
            viewer_theme.check_access("read")

    def test_manager_can_create_theme(self):
        theme = self.Theme.with_user(self.manager).create({"name": "Manager Theme"})
        self.assertTrue(theme.exists())

    def test_public_payload_uses_sudo_without_exposing_private_fields(self):
        theme = self.Theme.create(
            {
                "name": "Public Payload",
                "published": True,
                "is_default": False,
                "company_name": "Example",
            }
        )
        values = theme.sudo()._get_safe_theme_values()
        self.assertEqual(values["company_name"], "Example")
        self.assertNotIn("create_uid", values)
