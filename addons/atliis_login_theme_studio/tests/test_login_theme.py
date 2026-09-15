# -*- coding: utf-8 -*-

from odoo.exceptions import ValidationError
from odoo import fields
from odoo.tests.common import TransactionCase, tagged


@tagged("post_install", "-at_install")
class TestLoginTheme(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.Theme = cls.env["login.theme"]

    def test_validation_rejects_unsafe_url(self):
        with self.assertRaises(ValidationError):
            self.Theme.create(
                {
                    "name": "Unsafe URL",
                    "support_url": "javascript:alert(1)",
                }
            )

    def test_validation_rejects_invalid_colour(self):
        with self.assertRaises(ValidationError):
            self.Theme.create(
                {
                    "name": "Invalid Colour",
                    "primary_colour": "not-a-colour",
                }
            )

    def test_accessibility_score_reports_low_contrast(self):
        theme = self.Theme.create(
            {
                "name": "Low Contrast",
                "text_colour": "#ffffff",
                "card_colour": "#ffffff",
                "button_colour": "#111111",
                "button_text_colour": "#111111",
            }
        )
        self.assertLess(theme.accessibility_score, 100)
        self.assertIn("contrast", theme.accessibility_report.lower())

    def test_safe_theme_values_are_public_payload_only(self):
        theme = self.Theme.create(
            {
                "name": "Safe Payload",
                "heading": "Portal Login",
                "support_email": "support@example.com",
            }
        )
        values = theme._get_safe_theme_values()
        self.assertEqual(values["heading"], "Portal Login")
        self.assertEqual(values["support_email"], "support@example.com")
        self.assertIn("inline_style", values)
        self.assertNotIn("published", values)

    def test_background_settings_are_exported_as_css_variables(self):
        theme = self.Theme.create(
            {
                "name": "Background Settings",
                "background_type": "gradient",
                "background_position": "top",
                "background_size": "contain",
                "background_repeat": "repeat-x",
                "overlay_opacity": 0.4,
                "image_blur": 3,
                "image_brightness": 80,
                "image_saturation": 120,
                "form_alignment": "right",
                "vertical_alignment": "bottom",
                "card_shadow": "strong",
                "font_family": "inter",
                "link_hover_colour": "#123456",
            }
        )
        css = theme._get_safe_theme_values()["css_variables"]

        self.assertIn("linear-gradient", css["--login-background-image"])
        self.assertEqual(css["--login-background-position"], "top")
        self.assertEqual(css["--login-background-size"], "contain")
        self.assertEqual(css["--login-background-repeat"], "repeat-x")
        self.assertEqual(css["--login-background-overlay-opacity"], "0.4")
        self.assertEqual(css["--login-background-filter"], "blur(3px) brightness(80%) saturate(120%)")
        self.assertEqual(css["--login-form-justify"], "flex-end")
        self.assertEqual(css["--login-form-align"], "flex-end")
        self.assertIn("rgba", css["--login-card-shadow"])
        self.assertIn("Inter", css["--login-font-family"])
        self.assertEqual(css["--login-link-hover-colour"], "#123456")

    def test_background_image_css_url_is_not_html_escaped(self):
        theme = self.Theme.create(
            {
                "name": "Background Image CSS",
                "background_type": "image",
                "background_image": "R0lGODlhAQABAIAAAP///wAAACH5BAEAAAAALAAAAAABAAEAAAICRAEAOw==",
            }
        )
        inline_style = str(theme._get_safe_theme_values()["inline_style"])

        self.assertIn('url("/login_theme_studio/image/%s/background_image' % theme.id, inline_style)
        self.assertNotIn("&#39;", inline_style)
        self.assertNotIn("&#34;", inline_style)

    def test_announcement_dates_control_public_payload(self):
        future = fields.Datetime.add(fields.Datetime.now(), days=1)
        theme = self.Theme.create(
            {
                "name": "Future Announcement",
                "announcement_text": "Not yet",
                "announcement_date_start": future,
            }
        )

        self.assertEqual(theme._get_safe_theme_values()["announcement_text"], "")
