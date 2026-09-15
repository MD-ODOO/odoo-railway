# -*- coding: utf-8 -*-

from odoo.tests.common import HttpCase, tagged


TEST_IMAGE = "R0lGODlhAQABAIAAAP///wAAACH5BAEAAAAALAAAAAABAAEAAAICRAEAOw=="


@tagged("post_install", "-at_install")
class TestLoginThemeAuthenticationPages(HttpCase):
    def test_login_page_renders_with_theme_module_installed(self):
        response = self.url_open("/web/login")
        self.assertEqual(response.status_code, 200)
        self.assertIn("oe_login_form", response.text)

    def test_login_page_uses_published_theme_shell(self):
        Theme = self.env["login.theme"].sudo()
        Theme.search([]).write({"published": False, "is_default": False})
        theme = Theme.create(
            {
                "name": "Login Shell Test",
                "published": True,
                "heading": "Shell Heading",
                "footer_text": "Footer copy",
                "support_email": "help@example.com",
                "privacy_url": "https://example.com/privacy",
            }
        )
        self.env["website"].get_current_website().sudo().login_theme_id = theme
        self.env.cr.commit()

        response = self.url_open("/web/login")

        self.assertEqual(response.status_code, 200)
        self.assertIn("atliis-login-theme-form-vars", response.text)
        self.assertIn("o_login_theme_header", response.text)
        self.assertIn("o_login_theme_card", response.text)
        self.assertIn("Shell Heading", response.text)
        self.assertIn("Footer copy", response.text)
        self.assertIn("help@example.com", response.text)
        self.assertIn("https://example.com/privacy", response.text)
        self.assertNotIn("/web/binary/company_logo", response.text)

    def test_published_theme_background_image_is_publicly_served(self):
        Theme = self.env["login.theme"].sudo()
        Theme.search([]).write({"published": False, "is_default": False})
        theme = Theme.create(
            {
                "name": "Background Image Test",
                "published": True,
                "background_type": "image",
                "background_image": TEST_IMAGE,
            }
        )
        self.env["website"].get_current_website().sudo().login_theme_id = theme
        self.env.cr.commit()

        login_response = self.url_open("/web/login")
        image_url = "/login_theme_studio/image/%s/background_image" % theme.id

        self.assertEqual(login_response.status_code, 200)
        self.assertIn(image_url, login_response.text)
        image_response = self.url_open(image_url)
        self.assertEqual(image_response.status_code, 200)
        self.assertEqual(image_response.headers.get("X-Content-Type-Options"), "nosniff")

    def test_preview_requires_authenticated_user(self):
        theme = self.env["login.theme"].create({"name": "Preview Smoke"})
        response = self.url_open("/login_theme_studio/preview/%s" % theme.id, allow_redirects=False)
        self.assertIn(response.status_code, (303, 302))
