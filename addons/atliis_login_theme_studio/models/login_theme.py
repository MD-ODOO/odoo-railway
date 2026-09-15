# -*- coding: utf-8 -*-

import logging
import re
from urllib.parse import urlparse

from markupsafe import Markup

from odoo import api, fields, models, _
from odoo.exceptions import ValidationError

_logger = logging.getLogger(__name__)

COLOUR_RE = re.compile(
    r"^(#[0-9a-fA-F]{3}([0-9a-fA-F]{3})?|"
    r"rgba?\(\s*(25[0-5]|2[0-4]\d|1?\d?\d)\s*,\s*"
    r"(25[0-5]|2[0-4]\d|1?\d?\d)\s*,\s*"
    r"(25[0-5]|2[0-4]\d|1?\d?\d)"
    r"(\s*,\s*(0|1|0?\.\d+))?\s*\))$"
)

SAFE_FONT_FAMILIES = [
    ("system", "System UI"),
    ("inter", "Inter"),
    ("roboto", "Roboto"),
    ("open_sans", "Open Sans"),
    ("lato", "Lato"),
    ("montserrat", "Montserrat"),
    ("source_sans", "Source Sans 3"),
]

LOGIN_THEME_FIELD_HELP = {
    "name": "Internal name used to identify this login theme in Odoo.",
    "published": "Enable this theme for the live login page when it matches the current configuration.",
    "is_default": "Use this theme as the main fallback theme for the login page.",
    "company_name": "Company or product name displayed in the login header when enabled.",
    "page_title": "Browser tab title used on authentication pages.",
    "heading": "Main heading shown above the login form.",
    "subheading": "Short supporting line displayed under the main heading.",
    "welcome_message": "Optional formatted message shown in the login header.",
    "show_company_name": "Show or hide the company name in the login card.",
    "show_footer": "Show or hide the custom footer content under the login form.",
    "show_copyright": "Show or hide the copyright text in the login footer.",
    "show_support_details": "Show or hide support email, phone and support URL in the login footer.",
    "show_powered_by": "Show or hide the powered-by link in the login footer.",
    "show_privacy_link": "Show or hide the privacy policy link in the login footer.",
    "show_terms_link": "Show or hide the terms link in the login footer.",
    "show_help_link": "Show or hide the help link in the login footer.",
    "logo_source": "Choose whether the logo and favicon come from uploaded images or external URLs.",
    "logo": "Uploaded logo displayed on the login card.",
    "favicon": "Uploaded favicon used by authentication pages when available.",
    "logo_external_url": "Public URL for the logo when Logo Source is External URL.",
    "favicon_external_url": "Public URL for the favicon when Logo Source is External URL.",
    "logo_width": "Logo width in pixels. Leave enough space for mobile layouts.",
    "logo_height": "Logo height in pixels. Use 0 to keep the image's natural aspect ratio.",
    "logo_alignment": "Horizontal alignment of the logo and header content inside the login card.",
    "layout": "Overall login page layout used by the theme.",
    "form_width": "Maximum login form width in pixels.",
    "form_alignment": "Horizontal position of the login card on the page.",
    "vertical_alignment": "Vertical position of the login card on the page.",
    "card_padding": "Inner spacing of the login card in pixels.",
    "card_border_radius": "Corner radius of the login card in pixels.",
    "card_border_width": "Border thickness of the login card in pixels.",
    "card_border_colour": "Border colour used around the login card.",
    "card_shadow": "Depth of the shadow around the login card.",
    "card_opacity": "Card opacity from 0 to 1. Use 1 for a solid card.",
    "card_blur": "Backdrop blur behind the card in pixels, mainly useful with transparent cards.",
    "primary_colour": "Primary brand colour used for key accents.",
    "secondary_colour": "Secondary brand colour used in gradients and supporting accents.",
    "accent_colour": "Accent colour used for highlights and animated gradients.",
    "background_colour": "Base background colour used behind the login page.",
    "card_colour": "Background colour of the login card.",
    "heading_colour": "Colour of the main heading.",
    "text_colour": "Default text colour inside the login card.",
    "link_colour": "Default colour for links.",
    "link_hover_colour": "Colour shown when users hover over links.",
    "button_colour": "Primary login button background colour.",
    "button_hover_colour": "Primary login button colour on hover.",
    "button_text_colour": "Text colour inside the primary login button.",
    "input_background_colour": "Background colour of username and password fields.",
    "input_text_colour": "Text colour inside username and password fields.",
    "input_border_colour": "Border colour of username and password fields.",
    "error_colour": "Colour used for validation and error messages.",
    "success_colour": "Colour used for success messages.",
    "overlay_colour": "Colour of the overlay placed above image or gradient backgrounds.",
    "font_family": "Font family used by the login page.",
    "heading_font_size": "Heading font size in pixels.",
    "heading_font_weight": "Heading font weight, for example 400, 600 or 700.",
    "body_font_size": "Base body text size in pixels.",
    "button_font_size": "Login button text size in pixels.",
    "background_type": "Choose solid colour, gradient, animated gradient or image background.",
    "background_image": "Uploaded image used as the login page background.",
    "background_external_url": "Public image URL used as the background when no image is uploaded.",
    "background_position": "Position of the background image inside the viewport.",
    "background_size": "How the background image is scaled.",
    "background_repeat": "Whether and how the background image repeats.",
    "overlay_opacity": "Opacity of the background overlay from 0 to 1.",
    "image_blur": "Blur applied to the background image in pixels.",
    "image_brightness": "Brightness applied to the background image as a percentage.",
    "image_saturation": "Saturation applied to the background image as a percentage.",
    "username_label": "Label displayed above the username or email field.",
    "username_placeholder": "Placeholder text displayed inside the username or email field.",
    "password_label": "Label displayed above the password field.",
    "password_placeholder": "Placeholder text displayed inside the password field.",
    "login_button_text": "Text displayed on the login button.",
    "signup_link_text": "Text displayed for the sign-up link.",
    "reset_password_link_text": "Text displayed for the reset-password link.",
    "show_password_toggle": "Show or hide the password visibility toggle.",
    "show_signup_link": "Show or hide the sign-up link.",
    "show_reset_password_link": "Show or hide the reset-password link.",
    "show_oauth_providers": "Show or hide OAuth or SSO provider buttons.",
    "show_caps_lock_warning": "Show a warning when Caps Lock is active in password fields.",
    "autofocus_username": "Place the cursor in the username field when the page opens.",
    "autofocus_password": "Place the cursor in the password field when the username is already known.",
    "full_width_button": "Stretch the login button to the full card width.",
    "footer_text": "Formatted footer message displayed below the login form.",
    "copyright_text": "Copyright line displayed in the login footer.",
    "powered_by_text": "Text for the powered-by link.",
    "powered_by_url": "Destination URL for the powered-by link.",
    "support_email": "Support email shown in the login footer.",
    "support_phone": "Support phone number shown in the login footer.",
    "support_url": "Support page URL shown in the login footer.",
    "privacy_url": "Privacy policy URL shown in the login footer.",
    "terms_url": "Terms and conditions URL shown in the login footer.",
    "help_url": "Help or documentation URL shown in the login footer.",
    "announcement_type": "Visual style used for the announcement message.",
    "announcement_text": "Formatted announcement displayed on the login page.",
}


class LoginTheme(models.Model):
    _name = "login.theme"
    _description = "Login Theme"
    _order = "sequence, name, id"
    _check_company_auto = True

    def init(self):
        # Earlier builds used a website Many2one. The current integer field keeps Website optional.
        self.env.cr.execute("ALTER TABLE login_theme DROP CONSTRAINT IF EXISTS login_theme_website_id_fkey")
        self.env.cr.execute("UPDATE login_theme SET background_type = 'colour' WHERE background_type IN ('slideshow', 'video')")
        self._cleanup_obsolete_records()

    @api.model
    def _cleanup_obsolete_records(self):
        obsolete_record_names = [
            "access_login_theme_import_export_manager",
            "action_login_theme_import",
            "menu_login_theme_import",
            "model_login_theme_import_export_wizard",
            "view_login_theme_import_export_wizard_form",
            "access_login_theme_preset_viewer",
            "access_login_theme_preset_manager",
            "action_login_theme_preset",
            "menu_login_theme_preset",
            "view_login_theme_preset_list",
            "view_login_theme_preset_form",
            "view_login_theme_preset_search",
        ]
        obsolete_data_names = obsolete_record_names + [
            "preset_atliis_corporate",
            "preset_modern_split",
            "preset_minimal_light",
            "preset_dark_focus",
        ]
        IrModelData = self.env["ir.model.data"].sudo()
        for name in obsolete_record_names:
            record = self.env.ref("atliis_login_theme_studio.%s" % name, raise_if_not_found=False)
            if record:
                record.sudo().unlink()
        IrModelData.search(
            [
                ("module", "=", "atliis_login_theme_studio"),
                ("name", "in", obsolete_data_names),
            ]
        ).unlink()
        self.env["ir.model"].sudo().search([("model", "=", "login.theme.import.export.wizard")]).unlink()

    @api.model
    def fields_get(self, allfields=None, attributes=None):
        fields_data = super().fields_get(allfields=allfields, attributes=attributes)
        for field_name, help_text in LOGIN_THEME_FIELD_HELP.items():
            if field_name in fields_data:
                fields_data[field_name]["help"] = _(help_text)
        return fields_data

    name = fields.Char(required=True)
    active = fields.Boolean(default=True)
    published = fields.Boolean(default=False)
    publication_state = fields.Selection(
        [
            ("archived", "Archived"),
            ("draft", "Draft"),
            ("scheduled", "Scheduled"),
            ("published", "Published"),
            ("expired", "Expired"),
        ],
        compute="_compute_publication_state",
    )
    sequence = fields.Integer(default=10)
    is_default = fields.Boolean(default=False)
    company_id = fields.Many2one("res.company")
    website_id = fields.Integer(string="Website ID", help="Optional Website record ID. Kept as an integer so this module works without the Website app installed.")
    website_installed = fields.Boolean(compute="_compute_website_installed")
    domain_name = fields.Char()
    language_code = fields.Char()
    date_start = fields.Datetime()
    date_end = fields.Datetime()
    resolution_scope = fields.Selection(
        [
            ("domain", "Domain"),
            ("website", "Website"),
            ("company", "Company"),
            ("global", "Global"),
            ("inactive", "Inactive"),
        ],
        compute="_compute_resolution_metadata",
        store=True,
    )
    resolution_priority = fields.Integer(compute="_compute_resolution_metadata", store=True)
    applicability_warning = fields.Text(compute="_compute_resolution_metadata")

    company_name = fields.Char()
    page_title = fields.Char(default="Odoo")
    heading = fields.Char(default="Welcome")
    subheading = fields.Char()
    welcome_message = fields.Html(sanitize=True)
    footer_text = fields.Html(sanitize=True)
    copyright_text = fields.Char()
    support_email = fields.Char()
    support_phone = fields.Char()
    support_url = fields.Char()
    privacy_url = fields.Char()
    terms_url = fields.Char()
    help_url = fields.Char()
    powered_by_text = fields.Char(default="Powered by Atliis")
    powered_by_url = fields.Char(default="https://www.atliis.com")

    show_company_name = fields.Boolean(default=True)
    show_footer = fields.Boolean(default=True)
    show_copyright = fields.Boolean(default=True)
    show_support_details = fields.Boolean(default=True)
    show_powered_by = fields.Boolean(default=True)
    show_privacy_link = fields.Boolean(default=True)
    show_terms_link = fields.Boolean(default=True)
    show_help_link = fields.Boolean(default=True)
    show_return_to_website = fields.Boolean(default=False)

    logo = fields.Image(max_width=1024, max_height=1024)
    logo_dark = fields.Image(max_width=1024, max_height=1024)
    favicon = fields.Image(max_width=256, max_height=256)
    logo_external_url = fields.Char()
    favicon_external_url = fields.Char()
    logo_source = fields.Selection(
        [("upload", "Uploaded Image"), ("url", "External URL")],
        default="upload",
        required=True,
    )
    logo_width = fields.Integer(default=180)
    logo_height = fields.Integer(default=0)
    logo_position = fields.Selection(
        [("inside_card", "Inside Card"), ("top_bar", "Top Bar"), ("side_panel", "Side Panel")],
        default="inside_card",
        required=True,
    )
    logo_alignment = fields.Selection(
        [("left", "Left"), ("center", "Center"), ("right", "Right")],
        default="center",
        required=True,
    )

    layout = fields.Selection(
        [
            ("classic_center", "Classic Centre"),
            ("card_left", "Card Left"),
            ("card_right", "Card Right"),
            ("split_left", "Split Screen, Form Left"),
            ("split_right", "Split Screen, Form Right"),
            ("full_background", "Full Background"),
            ("glass", "Glassmorphism"),
            ("top_bar", "Branded Top Bar"),
            ("wave", "Wave Layout"),
            ("minimal", "Minimal Corporate"),
        ],
        required=True,
        default="classic_center",
    )
    form_width = fields.Integer(default=360)
    form_alignment = fields.Selection(
        [("left", "Left"), ("center", "Center"), ("right", "Right")],
        default="center",
        required=True,
    )
    vertical_alignment = fields.Selection(
        [("top", "Top"), ("middle", "Middle"), ("bottom", "Bottom")],
        default="middle",
        required=True,
    )
    card_padding = fields.Integer(default=32)
    card_border_radius = fields.Integer(default=16)
    card_border_width = fields.Integer(default=1)
    card_border_colour = fields.Char(default="#e5e7eb")
    card_shadow = fields.Selection(
        [("none", "None"), ("soft", "Soft"), ("medium", "Medium"), ("strong", "Strong")],
        default="soft",
        required=True,
    )
    card_opacity = fields.Float(default=1.0)
    card_blur = fields.Integer(default=0)
    side_panel_width = fields.Integer(default=50)
    mobile_layout = fields.Selection(
        [("stacked", "Stacked"), ("card", "Card"), ("minimal", "Minimal")],
        default="stacked",
        required=True,
    )

    primary_colour = fields.Char(default="#714B67")
    secondary_colour = fields.Char(default="#017E84")
    accent_colour = fields.Char(default="#F59E0B")
    background_colour = fields.Char(default="#f8fafc")
    card_colour = fields.Char(default="#ffffff")
    heading_colour = fields.Char(default="#111827")
    text_colour = fields.Char(default="#374151")
    link_colour = fields.Char(default="#714B67")
    link_hover_colour = fields.Char(default="#56384f")
    button_colour = fields.Char(default="#714B67")
    button_hover_colour = fields.Char(default="#56384f")
    button_text_colour = fields.Char(default="#ffffff")
    input_background_colour = fields.Char(default="#ffffff")
    input_text_colour = fields.Char(default="#111827")
    input_border_colour = fields.Char(default="#d1d5db")
    error_colour = fields.Char(default="#dc2626")
    success_colour = fields.Char(default="#16a34a")
    overlay_colour = fields.Char(default="rgba(0, 0, 0, 0.35)")

    font_family = fields.Selection(SAFE_FONT_FAMILIES, default="system", required=True)
    custom_font_url = fields.Char()
    heading_font_size = fields.Integer(default=28)
    heading_font_weight = fields.Integer(default=700)
    body_font_size = fields.Integer(default=16)
    button_font_size = fields.Integer(default=16)

    background_type = fields.Selection(
        [
            ("colour", "Solid Colour"),
            ("gradient", "Gradient"),
            ("animated_gradient", "Animated Gradient"),
            ("image", "Image"),
        ],
        default="colour",
        required=True,
    )
    background_image = fields.Image(max_width=2560, max_height=2560)
    background_mobile_image = fields.Image(max_width=1920, max_height=2560)
    background_external_url = fields.Char()
    background_video = fields.Binary(attachment=True)
    background_video_filename = fields.Char()
    background_video_url = fields.Char()
    background_position = fields.Selection(
        [("center", "Center"), ("top", "Top"), ("bottom", "Bottom"), ("left", "Left"), ("right", "Right")],
        default="center",
        required=True,
    )
    background_size = fields.Selection(
        [("cover", "Cover"), ("contain", "Contain"), ("auto", "Auto")],
        default="cover",
        required=True,
    )
    background_repeat = fields.Selection(
        [("no-repeat", "No Repeat"), ("repeat", "Repeat"), ("repeat-x", "Repeat Horizontally"), ("repeat-y", "Repeat Vertically")],
        default="no-repeat",
        required=True,
    )
    overlay_opacity = fields.Float(default=0.0)
    image_blur = fields.Integer(default=0)
    image_brightness = fields.Integer(default=100)
    image_saturation = fields.Integer(default=100)
    animation_speed = fields.Integer(default=20)
    slideshow_interval = fields.Integer(default=6000)
    background_image_ids = fields.One2many("login.theme.background.image", "theme_id", string="Slideshow Images")

    username_label = fields.Char(default="Email")
    username_placeholder = fields.Char(default="Enter your email")
    password_label = fields.Char(default="Password")
    password_placeholder = fields.Char(default="Enter your password")
    login_button_text = fields.Char(default="Log in")
    signup_link_text = fields.Char(default="Don't have an account?")
    reset_password_link_text = fields.Char(default="Reset Password")
    return_to_website_text = fields.Char(default="Return to website")

    show_password_toggle = fields.Boolean(default=True)
    show_signup_link = fields.Boolean(default=True)
    show_reset_password_link = fields.Boolean(default=True)
    show_database_manager_link = fields.Boolean(default=False)
    show_database_selector_link = fields.Boolean(default=True)
    show_oauth_providers = fields.Boolean(default=True)
    show_remember_username = fields.Boolean(default=False)
    show_caps_lock_warning = fields.Boolean(default=True)
    autofocus_username = fields.Boolean(default=True)
    autofocus_password = fields.Boolean(default=False)
    full_width_button = fields.Boolean(default=True)

    side_panel_heading = fields.Char()
    side_panel_content = fields.Html(sanitize=True)
    announcement_text = fields.Html(sanitize=True)
    announcement_type = fields.Selection(
        [
            ("information", "Information"),
            ("success", "Success"),
            ("warning", "Warning"),
            ("maintenance", "Maintenance"),
            ("security", "Security"),
        ],
        default="information",
    )
    announcement_date_start = fields.Datetime()
    announcement_date_end = fields.Datetime()
    call_to_action_text = fields.Char()
    call_to_action_url = fields.Char()

    high_contrast = fields.Boolean(default=False)
    reduced_motion = fields.Boolean(default=True)
    rtl_support = fields.Boolean(default=True)
    contrast_warning = fields.Text(compute="_compute_contrast_warning")
    accessibility_score = fields.Integer(compute="_compute_accessibility_report")
    accessibility_report = fields.Text(compute="_compute_accessibility_report")

    @api.depends_context("uid")
    def _compute_website_installed(self):
        installed = "website" in self.env.registry
        for theme in self:
            theme.website_installed = installed

    @api.depends("active", "published", "date_start", "date_end")
    def _compute_publication_state(self):
        now = fields.Datetime.now()
        for theme in self:
            if not theme.active:
                state = "archived"
            elif not theme.published:
                state = "draft"
            elif theme.date_start and theme.date_start > now:
                state = "scheduled"
            elif theme.date_end and theme.date_end < now:
                state = "expired"
            else:
                state = "published"
            theme.publication_state = state

    @api.depends(
        "active",
        "published",
        "is_default",
        "domain_name",
        "website_id",
        "company_id",
        "date_start",
        "date_end",
    )
    def _compute_resolution_metadata(self):
        now = fields.Datetime.now()
        for theme in self:
            warnings = []
            if not theme.active:
                scope = "inactive"
                priority = 0
                warnings.append(_("Archived themes are never selected."))
            elif theme.domain_name:
                scope = "domain"
                priority = 100
            elif theme.website_id:
                scope = "website"
                priority = 80
            elif theme.company_id:
                scope = "company"
                priority = 60
            else:
                scope = "global"
                priority = 40 if theme.is_default else 20

            if not theme.published:
                warnings.append(_("Only published themes are shown to public users."))
            if theme.date_start and theme.date_start > now:
                warnings.append(_("This theme is scheduled for the future."))
            if theme.date_end and theme.date_end < now:
                warnings.append(_("This theme has expired."))
            if theme.website_id and not theme.website_installed:
                warnings.append(_("Website-specific matching is configured by Website ID; install Website for automatic request website detection."))
            if not theme.domain_name and not theme.website_id and not theme.company_id and not theme.is_default:
                warnings.append(_("Global fallback themes should be marked as Default or selected in Login Studio settings."))

            theme.resolution_scope = scope
            theme.resolution_priority = priority
            theme.applicability_warning = "\n".join(warnings)

    @api.depends(
        "background_colour",
        "card_colour",
        "text_colour",
        "heading_colour",
        "button_colour",
        "button_text_colour",
        "link_colour",
        "input_background_colour",
        "input_text_colour",
        "input_border_colour",
    )
    def _compute_contrast_warning(self):
        for theme in self:
            theme.contrast_warning = theme.accessibility_report

    @api.depends(
        "background_colour",
        "card_colour",
        "text_colour",
        "heading_colour",
        "button_colour",
        "button_text_colour",
        "link_colour",
        "input_background_colour",
        "input_text_colour",
        "input_border_colour",
        "body_font_size",
        "button_font_size",
        "heading_font_size",
        "show_password_toggle",
        "show_caps_lock_warning",
        "reduced_motion",
    )
    def _compute_accessibility_report(self):
        checks = [
            ("Text on card", "text_colour", "card_colour", 4.5),
            ("Heading on card", "heading_colour", "card_colour", 3.0),
            ("Button text", "button_text_colour", "button_colour", 4.5),
            ("Link on card", "link_colour", "card_colour", 4.5),
            ("Input text", "input_text_colour", "input_background_colour", 4.5),
            ("Input border", "input_border_colour", "input_background_colour", 3.0),
        ]
        for theme in self:
            warnings = []
            passed = 0
            total = len(checks) + 4
            for label, foreground, background, minimum in checks:
                ratio = theme._contrast_ratio(theme[foreground], theme[background])
                if ratio is None:
                    warnings.append(_("%s contrast could not be checked because one colour is not a hex value.") % label)
                    continue
                if ratio < minimum:
                    warnings.append(
                        _("%(label)s contrast ratio is %(ratio).2f:1; recommended minimum is %(minimum).1f:1.")
                        % {"label": label, "ratio": ratio, "minimum": minimum}
                    )
                else:
                    passed += 1
            if theme.body_font_size >= 14:
                passed += 1
            else:
                warnings.append(_("Body text should be at least 14px for comfortable reading."))
            if theme.button_font_size >= 14:
                passed += 1
            else:
                warnings.append(_("Button text should be at least 14px."))
            if theme.show_password_toggle and theme.show_caps_lock_warning:
                passed += 1
            else:
                warnings.append(_("Enable password visibility and Caps Lock feedback for better authentication usability."))
            if theme.reduced_motion:
                passed += 1
            else:
                warnings.append(_("Reduced-motion support should remain enabled."))
            theme.accessibility_score = int(round((passed / total) * 100)) if total else 0
            theme.accessibility_report = "\n".join(warnings)

    @api.constrains("date_start", "date_end", "announcement_date_start", "announcement_date_end")
    def _check_date_ranges(self):
        for theme in self:
            if theme.date_start and theme.date_end and theme.date_start > theme.date_end:
                raise ValidationError(_("Theme start date must be before the end date."))
            if (
                theme.announcement_date_start
                and theme.announcement_date_end
                and theme.announcement_date_start > theme.announcement_date_end
            ):
                raise ValidationError(_("Announcement start date must be before the end date."))

    @api.constrains("domain_name", "language_code", "website_id")
    def _check_resolution_scope_values(self):
        for theme in self:
            if theme.domain_name:
                parsed = urlparse(theme.domain_name if "://" in theme.domain_name else "//%s" % theme.domain_name)
                if parsed.scheme and parsed.scheme not in ("", "http", "https"):
                    raise ValidationError(_("Domain names must not use unsafe protocols."))
                host = parsed.netloc or parsed.path
                if "/" in host or ":" in host:
                    raise ValidationError(_("Enter a bare domain name without protocol, port or path."))
            if theme.language_code and not re.match(r"^[a-z]{2}(_[A-Z]{2})?$", theme.language_code):
                raise ValidationError(_("Language code must look like en or en_US."))
            if theme.website_id and theme.website_id < 0:
                raise ValidationError(_("Website ID must be a positive number."))

    @api.constrains(
        "logo_external_url",
        "favicon_external_url",
        "support_url",
        "privacy_url",
        "terms_url",
        "help_url",
        "powered_by_url",
        "custom_font_url",
        "background_external_url",
        "background_video_url",
        "call_to_action_url",
    )
    def _check_safe_urls(self):
        url_fields = [
            "logo_external_url",
            "favicon_external_url",
            "support_url",
            "privacy_url",
            "terms_url",
            "help_url",
            "powered_by_url",
            "custom_font_url",
            "background_external_url",
            "background_video_url",
            "call_to_action_url",
        ]
        for theme in self:
            for field_name in url_fields:
                value = theme[field_name]
                if value:
                    theme._validate_external_url(value)

    @api.constrains(
        "primary_colour",
        "secondary_colour",
        "accent_colour",
        "background_colour",
        "card_colour",
        "heading_colour",
        "text_colour",
        "link_colour",
        "link_hover_colour",
        "button_colour",
        "button_hover_colour",
        "button_text_colour",
        "input_background_colour",
        "input_text_colour",
        "input_border_colour",
        "error_colour",
        "success_colour",
        "overlay_colour",
        "card_border_colour",
    )
    def _check_colour_values(self):
        colour_fields = [
            "primary_colour",
            "secondary_colour",
            "accent_colour",
            "background_colour",
            "card_colour",
            "heading_colour",
            "text_colour",
            "link_colour",
            "link_hover_colour",
            "button_colour",
            "button_hover_colour",
            "button_text_colour",
            "input_background_colour",
            "input_text_colour",
            "input_border_colour",
            "error_colour",
            "success_colour",
            "overlay_colour",
            "card_border_colour",
        ]
        for theme in self:
            for field_name in colour_fields:
                value = theme[field_name]
                if value:
                    theme._validate_colour_value(value)

    @api.constrains(
        "logo_width",
        "logo_height",
        "form_width",
        "card_padding",
        "card_border_radius",
        "card_border_width",
        "card_opacity",
        "card_blur",
        "side_panel_width",
        "heading_font_size",
        "heading_font_weight",
        "body_font_size",
        "button_font_size",
        "overlay_opacity",
        "image_blur",
        "image_brightness",
        "image_saturation",
        "animation_speed",
        "slideshow_interval",
    )
    def _check_numeric_ranges(self):
        ranges = {
            "logo_width": (0, 800),
            "logo_height": (0, 400),
            "form_width": (240, 720),
            "card_padding": (0, 96),
            "card_border_radius": (0, 100),
            "card_border_width": (0, 20),
            "card_opacity": (0, 1),
            "card_blur": (0, 40),
            "side_panel_width": (20, 80),
            "heading_font_size": (16, 72),
            "heading_font_weight": (100, 900),
            "body_font_size": (12, 24),
            "button_font_size": (12, 24),
            "overlay_opacity": (0, 1),
            "image_blur": (0, 40),
            "image_brightness": (20, 200),
            "image_saturation": (0, 200),
            "animation_speed": (5, 120),
            "slideshow_interval": (2000, 60000),
        }
        for theme in self:
            for field_name, (minimum, maximum) in ranges.items():
                value = theme[field_name]
                if value is not False and value is not None and not minimum <= value <= maximum:
                    raise ValidationError(
                        _("%(field)s must be between %(minimum)s and %(maximum)s.")
                        % {
                            "field": theme._fields[field_name].string,
                            "minimum": minimum,
                            "maximum": maximum,
                        }
                    )

    @api.constrains("is_default", "domain_name", "website_id", "company_id", "active")
    def _check_default_conflicts(self):
        for theme in self.filtered("is_default"):
            domain = [
                ("id", "!=", theme.id),
                ("active", "=", True),
                ("is_default", "=", True),
                ("domain_name", "=", theme.domain_name or False),
                ("website_id", "=", theme.website_id or 0),
                ("company_id", "=", theme.company_id.id if theme.company_id else False),
            ]
            if self.search_count(domain, limit=1):
                raise ValidationError(_("Another default theme already exists for the same domain, website and company scope."))

    @api.constrains("published", "domain_name", "website_id", "company_id", "active", "date_start", "date_end")
    def _check_published_scope_conflicts(self):
        for theme in self.filtered(lambda item: item.active and item.published):
            scope_domain = theme._get_conflict_scope_domain()
            if scope_domain and self.search_count([("id", "!=", theme.id)] + scope_domain, limit=1):
                raise ValidationError(_("Another active published theme already targets the same resolution scope. Adjust domain, website, company or archive one theme."))

    def _get_conflict_scope_domain(self):
        self.ensure_one()
        if self.domain_name:
            return [
                ("active", "=", True),
                ("published", "=", True),
                ("domain_name", "=", self.domain_name),
            ]
        if self.website_id:
            return [
                ("active", "=", True),
                ("published", "=", True),
                ("domain_name", "=", False),
                ("website_id", "=", self.website_id),
            ]
        if self.company_id:
            return [
                ("active", "=", True),
                ("published", "=", True),
                ("domain_name", "=", False),
                ("website_id", "=", 0),
                ("company_id", "=", self.company_id.id),
            ]
        if self.is_default:
            return [
                ("active", "=", True),
                ("published", "=", True),
                ("is_default", "=", True),
                ("domain_name", "=", False),
                ("website_id", "=", 0),
                ("company_id", "=", False),
            ]
        return []

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            self._normalize_resolution_vals(vals)
        return super().create(vals_list)

    def write(self, vals):
        vals = dict(vals)
        self._normalize_resolution_vals(vals)
        return super().write(vals)

    @api.model
    def _normalize_resolution_vals(self, vals):
        if vals.get("domain_name"):
            vals["domain_name"] = self._normalize_domain_name(vals["domain_name"])
        if "website_id" in vals and not vals.get("website_id"):
            vals["website_id"] = 0

    @api.model
    def _normalize_domain_name(self, domain_name):
        value = (domain_name or "").strip().lower()
        if not value:
            return False
        parsed = urlparse(value if "://" in value else "//%s" % value)
        return (parsed.netloc or parsed.path).split("/")[0].split(":")[0]

    def _validate_external_url(self, url):
        value = url.strip()
        if re.search(r"[<>\r\n]", value):
            raise ValidationError(_("URLs must not contain HTML or line-break characters: %s") % url)
        parsed = urlparse(value)
        if parsed.scheme not in ("http", "https") or not parsed.netloc:
            raise ValidationError(_("Only safe HTTP and HTTPS URLs are allowed: %s") % url)
        return True

    def _validate_colour_value(self, value):
        if not COLOUR_RE.match(value.strip()):
            raise ValidationError(_("Invalid colour value: %s") % value)
        return True

    def _contrast_ratio(self, foreground, background):
        foreground_rgb = self._hex_to_rgb(foreground)
        background_rgb = self._hex_to_rgb(background)
        if not foreground_rgb or not background_rgb:
            return None
        foreground_luminance = self._relative_luminance(foreground_rgb)
        background_luminance = self._relative_luminance(background_rgb)
        lighter = max(foreground_luminance, background_luminance)
        darker = min(foreground_luminance, background_luminance)
        return (lighter + 0.05) / (darker + 0.05)

    @api.model
    def _hex_to_rgb(self, value):
        value = (value or "").strip()
        if not value.startswith("#"):
            return None
        value = value[1:]
        if len(value) == 3:
            value = "".join(part * 2 for part in value)
        if len(value) != 6 or not re.match(r"^[0-9a-fA-F]{6}$", value):
            return None
        return tuple(int(value[index:index + 2], 16) for index in (0, 2, 4))

    @api.model
    def _relative_luminance(self, rgb):
        channels = []
        for channel in rgb:
            value = channel / 255.0
            channels.append(value / 12.92 if value <= 0.03928 else ((value + 0.055) / 1.055) ** 2.4)
        return 0.2126 * channels[0] + 0.7152 * channels[1] + 0.0722 * channels[2]

    def _is_theme_currently_active(self):
        now = fields.Datetime.now()
        self.ensure_one()
        scheduling_enabled = self.env["ir.config_parameter"].sudo().get_param(
            "atliis_login_theme_studio.enable_theme_scheduling", "True"
        ) in ("1", "True", "true")
        return (
            self.active
            and self.published
            and (
                not scheduling_enabled
                or (
                    (not self.date_start or self.date_start <= now)
                    and (not self.date_end or self.date_end >= now)
                )
            )
        )

    def _get_safe_theme_values(self):
        self.ensure_one()
        values = {
            "id": self.id,
            "name": self.name,
            "layout": self.layout,
            "page_title": self.page_title,
            "heading": self.heading,
            "subheading": self.subheading,
            "company_name": self.company_name,
            "welcome_message": self.welcome_message,
            "footer_text": self.footer_text,
            "copyright_text": self.copyright_text,
            "powered_by_text": self.powered_by_text,
            "powered_by_url": self.powered_by_url,
            "support_email": self.support_email,
            "support_phone": self.support_phone,
            "support_url": self.support_url,
            "privacy_url": self.privacy_url,
            "terms_url": self.terms_url,
            "help_url": self.help_url,
            "announcement_text": self._get_login_theme_announcement_text(),
            "announcement_type": self.announcement_type,
            "side_panel_heading": self.side_panel_heading,
            "side_panel_content": self.side_panel_content,
            "show_footer": self.show_footer,
            "show_website_header": self._get_login_theme_show_website_header(),
            "show_website_footer": self._get_login_theme_show_website_footer(),
            "website_chrome_class": self._get_login_theme_website_chrome_class(),
            "show_company_name": self.show_company_name,
            "show_copyright": self.show_copyright,
            "show_powered_by": self.show_powered_by,
            "show_support_details": self.show_support_details,
            "show_privacy_link": self.show_privacy_link,
            "show_terms_link": self.show_terms_link,
            "show_help_link": self.show_help_link,
            "username_label": self.username_label,
            "username_placeholder": self.username_placeholder,
            "password_label": self.password_label,
            "password_placeholder": self.password_placeholder,
            "login_button_text": self.login_button_text,
            "signup_link_text": self.signup_link_text,
            "reset_password_link_text": self.reset_password_link_text,
            "return_to_website_text": self.return_to_website_text,
            "show_password_toggle": self.show_password_toggle,
            "show_signup_link": self.show_signup_link,
            "show_reset_password_link": self.show_reset_password_link,
            "show_database_manager_link": self.show_database_manager_link,
            "show_database_selector_link": self.show_database_selector_link,
            "show_oauth_providers": self.show_oauth_providers,
            "show_caps_lock_warning": self.show_caps_lock_warning,
            "autofocus_username": self.autofocus_username,
            "autofocus_password": self.autofocus_password,
            "full_width_button": self.full_width_button,
            "logo_alignment": self.logo_alignment,
            "form_alignment": self.form_alignment,
            "vertical_alignment": self.vertical_alignment,
            "logo_url": self._get_login_theme_logo_url(),
            "favicon_url": self._get_login_theme_favicon_url(),
        }
        css_variables = self._get_theme_css_variables()
        values["css_variables"] = css_variables
        values["inline_style"] = Markup("; ".join("%s: %s" % item for item in css_variables.items()))
        return values

    def _get_login_theme_show_website_header(self):
        website = self._get_current_website()
        return bool(not website or website.login_theme_show_website_chrome)

    def _get_login_theme_show_website_footer(self):
        website = self._get_current_website()
        return bool(not website or website.login_theme_show_website_chrome)

    def _get_login_theme_website_chrome_class(self):
        classes = []
        if not self._get_login_theme_show_website_header() or not self._get_login_theme_show_website_footer():
            classes.append("o_login_theme_hide_website_chrome")
        return " ".join(classes)

    def _get_theme_css_variables(self):
        self.ensure_one()
        mapping = {
            "--login-primary-colour": self.primary_colour,
            "--login-secondary-colour": self.secondary_colour,
            "--login-accent-colour": self.accent_colour,
            "--login-background-colour": self.background_colour,
            "--login-card-colour": self.card_colour,
            "--login-heading-colour": self.heading_colour,
            "--login-text-colour": self.text_colour,
            "--login-link-colour": self.link_colour,
            "--login-link-hover-colour": self.link_hover_colour,
            "--login-button-colour": self.button_colour,
            "--login-button-hover-colour": self.button_hover_colour,
            "--login-button-text-colour": self.button_text_colour,
            "--login-input-background-colour": self.input_background_colour,
            "--login-input-text-colour": self.input_text_colour,
            "--login-input-border-colour": self.input_border_colour,
            "--login-error-colour": self.error_colour,
            "--login-success-colour": self.success_colour,
            "--login-card-border-colour": self.card_border_colour,
            "--login-card-border-width": "%spx" % self.card_border_width,
            "--login-card-radius": "%spx" % self.card_border_radius,
            "--login-card-padding": "%spx" % self.card_padding,
            "--login-card-opacity": str(self.card_opacity),
            "--login-card-blur": "%spx" % self.card_blur,
            "--login-card-shadow": self._get_login_theme_card_shadow(),
            "--login-form-width": "%spx" % self.form_width,
            "--login-form-justify": self._get_login_theme_justify_content(),
            "--login-form-align": self._get_login_theme_align_items(),
            "--login-logo-width": "%spx" % self.logo_width if self.logo_width else "auto",
            "--login-logo-height": "%spx" % self.logo_height if self.logo_height else "auto",
            "--login-heading-font-size": "%spx" % self.heading_font_size,
            "--login-heading-font-weight": str(self.heading_font_weight),
            "--login-body-font-size": "%spx" % self.body_font_size,
            "--login-button-font-size": "%spx" % self.button_font_size,
            "--login-font-family": self._get_login_theme_font_family(),
            "--login-background-image": "none",
            "--login-background-size": self.background_size,
            "--login-background-position": self.background_position,
            "--login-background-repeat": self.background_repeat,
            "--login-background-overlay-colour": self.overlay_colour,
            "--login-background-overlay-opacity": str(self.overlay_opacity),
            "--login-background-filter": "blur(%spx) brightness(%s%%) saturate(%s%%)"
            % (self.image_blur, self.image_brightness, self.image_saturation),
            "--login-background-animation": "none",
        }
        if self.background_type == "gradient":
            mapping["--login-background-image"] = "linear-gradient(135deg, %s, %s)" % (
                self.primary_colour,
                self.secondary_colour,
            )
        elif self.background_type == "animated_gradient":
            mapping["--login-background-image"] = "linear-gradient(120deg, %s, %s, %s)" % (
                self.primary_colour,
                self.secondary_colour,
                self.accent_colour,
            )
            mapping["--login-background-size"] = "300% 300%"
            mapping["--login-background-animation"] = "o-login-theme-background %ss ease infinite" % self.animation_speed
        elif self.background_type == "image" and self.background_external_url:
            mapping["--login-background-image"] = self._get_login_theme_css_url(self.background_external_url)
        elif self.background_type == "image" and self.background_image:
            mapping["--login-background-image"] = self._get_login_theme_css_url(self._get_login_theme_asset_url("background_image"))
        return {key: value for key, value in mapping.items() if value}

    def _get_login_theme_card_shadow(self):
        self.ensure_one()
        shadows = {
            "none": "none",
            "soft": "0 18px 50px rgba(15, 23, 42, 0.16)",
            "medium": "0 24px 70px rgba(15, 23, 42, 0.24)",
            "strong": "0 32px 90px rgba(15, 23, 42, 0.34)",
        }
        return shadows.get(self.card_shadow, shadows["soft"])

    def _get_login_theme_justify_content(self):
        self.ensure_one()
        values = {
            "left": "flex-start",
            "center": "center",
            "right": "flex-end",
        }
        return values.get(self.form_alignment, "center")

    def _get_login_theme_align_items(self):
        self.ensure_one()
        values = {
            "top": "flex-start",
            "middle": "center",
            "bottom": "flex-end",
        }
        return values.get(self.vertical_alignment, "center")

    def _get_login_theme_font_family(self):
        self.ensure_one()
        values = {
            "system": "system-ui, -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif",
            "inter": "Inter, system-ui, sans-serif",
            "roboto": "Roboto, Arial, sans-serif",
            "open_sans": "'Open Sans', Arial, sans-serif",
            "lato": "Lato, Arial, sans-serif",
            "montserrat": "Montserrat, Arial, sans-serif",
            "source_sans": "'Source Sans 3', Arial, sans-serif",
        }
        return values.get(self.font_family, values["system"])

    def _get_login_theme_css_url(self, url):
        value = (url or "").strip()
        value = value.replace("\\", "\\\\").replace('"', '\\"').replace("\n", "").replace("\r", "")
        return 'url("%s")' % value

    def _get_login_theme_announcement_text(self):
        self.ensure_one()
        now = fields.Datetime.now()
        if self.announcement_date_start and self.announcement_date_start > now:
            return ""
        if self.announcement_date_end and self.announcement_date_end < now:
            return ""
        return self.announcement_text

    @api.model
    def _get_effective_login_theme(self):
        return self._get_theme_for_request()

    @api.model
    def _get_public_theme_values(self):
        """Return the safe public theme payload used by authentication QWeb."""
        request = self.env.context.get("login_theme_request")
        if request is not None and hasattr(request, "_atliis_login_theme_values"):
            return request._atliis_login_theme_values
        try:
            if self._is_native_login_forced():
                values = {}
            else:
                theme = self.sudo()._get_theme_for_request()
                values = theme._get_safe_theme_values() if theme else {}
            if request is not None:
                request._atliis_login_theme_values = values
            return values
        except Exception:
            _logger.exception("Login theme rendering failed; falling back to native login.")
            return {}

    @api.model
    def _is_native_login_forced(self):
        request = self.env.context.get("login_theme_request")
        if request and request.args.get("login_theme_safe_mode") == "1":
            return True
        return False

    @api.model
    def _get_theme_for_request(self, domain_name=None, website=None, company=None):
        Theme = self.sudo()
        base_domain = Theme._get_selectable_theme_domain()
        domain_name = Theme._normalize_domain_name(domain_name or self._get_current_domain())
        company = company or self._get_current_company()
        website = website or self._get_current_website()
        website_theme = Theme._get_website_configured_theme(website)
        if website_theme:
            _logger.debug("Resolved login theme %s from selected website settings.", website_theme.display_name)
            return website_theme
        if "website" in self.env.registry:
            return Theme.browse()
        website_id = Theme._get_website_id(website)
        candidates = []
        if self.env["ir.config_parameter"].sudo().get_param(
            "atliis_login_theme_studio.enable_domain_theme_resolution", "True"
        ) in ("1", "True", "true") and domain_name:
            candidates.append(("domain", base_domain + [("domain_name", "=", domain_name)]))
        if website_id:
            candidates.append(("website", base_domain + [("website_id", "=", website_id), ("domain_name", "=", False)]))
        if company:
            candidates.append(("company", base_domain + [("company_id", "=", company.id), ("website_id", "=", 0), ("domain_name", "=", False)]))
        candidates.append(("global_default", base_domain + [("is_default", "=", True), ("company_id", "=", False), ("website_id", "=", 0), ("domain_name", "=", False)]))
        for scope, candidate_domain in candidates:
            theme = Theme.search(candidate_domain, order="sequence, id", limit=1)
            if theme:
                _logger.debug("Resolved login theme %s using %s scope.", theme.display_name, scope)
                return theme
        fallback_mode = self.env["ir.config_parameter"].sudo().get_param(
            "atliis_login_theme_studio.fallback_mode", "configured"
        )
        if fallback_mode != "configured":
            return Theme.browse()
        configured_theme = Theme._get_configured_default_theme()
        return configured_theme if configured_theme and configured_theme._is_theme_currently_active() else Theme.browse()

    @api.model
    def _get_website_configured_theme(self, website):
        theme = getattr(website, "login_theme_id", False) if website else False
        return theme.sudo() if theme and theme.sudo()._is_theme_currently_active() else self.browse()

    @api.model
    def _get_selectable_theme_domain(self):
        now = fields.Datetime.now()
        domain = [
            ("active", "=", True),
            ("published", "=", True),
        ]
        if self.env["ir.config_parameter"].sudo().get_param(
            "atliis_login_theme_studio.enable_theme_scheduling", "True"
        ) in ("1", "True", "true"):
            domain += [
                "|",
                ("date_start", "=", False),
                ("date_start", "<=", now),
                "|",
                ("date_end", "=", False),
                ("date_end", ">=", now),
            ]
        return domain

    @api.model
    def _get_website_id(self, website):
        return website.id if website else 0

    @api.model
    def _get_current_company(self):
        request = self.env.context.get("login_theme_request")
        website = request and getattr(request, "website", None)
        if website and getattr(website, "company_id", None):
            return website.company_id
        return self.env.company

    @api.model
    def _get_configured_default_theme(self):
        theme_id = self.env["ir.config_parameter"].sudo().get_param(
            "atliis_login_theme_studio.default_login_theme_id"
        )
        if theme_id and theme_id.isdigit():
            return self.sudo().browse(int(theme_id)).exists()
        return self.browse()

    @api.model
    def _get_current_domain(self):
        request = self.env.context.get("login_theme_request")
        host = request and getattr(request, "host", None)
        return (host or "").split(":")[0].lower()

    @api.model
    def _get_current_website(self):
        if "website" not in self.env.registry:
            return False
        request = self.env.context.get("login_theme_request")
        website = request and getattr(request, "website", None)
        if website:
            return website
        get_current_website = getattr(self.env["website"], "get_current_website", None)
        if get_current_website:
            try:
                return get_current_website()
            except Exception:
                _logger.debug("Could not resolve current website for login theme.", exc_info=True)
        return self.env["website"].browse()

    def action_publish(self):
        self._validate_publishable()
        self.write({"published": True})

    def action_unpublish(self):
        self.write({"published": False})

    def action_reset_to_draft(self):
        self.write({"published": False})

    def action_open_preview(self):
        self.ensure_one()
        return {
            "type": "ir.actions.act_url",
            "name": _("Theme Preview"),
            "url": "/login_theme_studio/preview/%s" % self.id,
            "target": "new",
        }

    def action_run_accessibility_check(self):
        self.ensure_one()
        message = self.accessibility_report or _("No accessibility issues detected.")
        return {
            "type": "ir.actions.client",
            "tag": "display_notification",
            "params": {
                "title": _("Accessibility Score: %s%%") % self.accessibility_score,
                "message": message,
                "type": "success" if not self.accessibility_report else "warning",
                "sticky": bool(self.accessibility_report),
            },
        }

    def _validate_publishable(self):
        for theme in self:
            errors = []
            if not theme.active:
                errors.append(_("Archived themes cannot be published."))
            if theme.date_start and theme.date_end and theme.date_start > theme.date_end:
                errors.append(_("Theme start date must be before the end date."))
            if theme.logo_source == "url" and theme.logo_external_url:
                theme._validate_external_url(theme.logo_external_url)
            if theme.background_type == "image" and not theme.background_image and not theme.background_external_url:
                errors.append(_("Image backgrounds require an uploaded image or an external image URL."))
            if errors:
                _logger.warning("Publishing validation failed for login theme %s: %s", theme.display_name, "; ".join(errors))
                raise ValidationError("\n".join(errors))

    def _get_login_theme_logo_url(self):
        self.ensure_one()
        if self.logo_source == "url" and self.logo_external_url:
            return self.logo_external_url
        if self.logo:
            return self._get_login_theme_asset_url("logo")
        return ""

    def _get_login_theme_favicon_url(self):
        self.ensure_one()
        if self.logo_source == "url" and self.favicon_external_url:
            return self.favicon_external_url
        if self.favicon:
            return self._get_login_theme_asset_url("favicon")
        return ""

    def _get_login_theme_asset_url(self, field_name):
        self.ensure_one()
        cache_key = fields.Datetime.to_string(self.write_date or self.create_date or fields.Datetime.now()).replace(" ", "-")
        return "/login_theme_studio/image/%s/%s?unique=%s" % (self.id, field_name, cache_key)


class LoginThemeBackgroundImage(models.Model):
    _name = "login.theme.background.image"
    _description = "Login Theme Background Image"
    _order = "sequence, id"

    theme_id = fields.Many2one("login.theme", required=True, ondelete="cascade")
    sequence = fields.Integer(default=10)
    name = fields.Char(required=True)
    image = fields.Image(max_width=2560, max_height=2560)
    external_url = fields.Char()
    alt_text = fields.Char()
    active = fields.Boolean(default=True)

    @api.constrains("external_url")
    def _check_external_url(self):
        for slide in self.filtered("external_url"):
            slide.theme_id._validate_external_url(slide.external_url)
