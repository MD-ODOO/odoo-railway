# -*- coding: utf-8 -*-

import base64

from werkzeug.exceptions import Forbidden, NotFound

from odoo import http
from odoo.http import request
from odoo.tools.mimetypes import guess_mimetype


PREVIEW_DEVICES = {
    "desktop": {
        "name": "Desktop",
        "width": 1366,
        "height": 768,
    },
    "tablet": {
        "name": "Tablet",
        "width": 820,
        "height": 1180,
    },
    "mobile": {
        "name": "Mobile",
        "width": 390,
        "height": 844,
    },
}

THEME_IMAGE_FIELDS = {"logo", "favicon", "background_image"}


class LoginThemePreview(http.Controller):
    def _get_preview_theme(self, theme_id):
        if not request.env.user.has_group("atliis_login_theme_studio.group_login_theme_manager"):
            raise Forbidden()
        theme = request.env["login.theme"].browse(int(theme_id)).exists()
        if not theme:
            raise NotFound()
        theme.check_access("read")
        return theme

    @http.route("/login_theme_studio/preview/<int:theme_id>", type="http", auth="user")
    def preview_shell(self, theme_id, **kwargs):
        theme = self._get_preview_theme(theme_id)
        response = request.render(
            "atliis_login_theme_studio.login_theme_preview_shell",
            {
                "theme": theme,
                "devices": [
                    {"key": key, **device}
                    for key, device in PREVIEW_DEVICES.items()
                ],
            },
        )
        response.headers["X-Frame-Options"] = "SAMEORIGIN"
        return response

    @http.route("/login_theme_studio/image/<int:theme_id>/<string:field_name>", type="http", auth="public")
    def theme_image(self, theme_id, field_name, **kwargs):
        if field_name not in THEME_IMAGE_FIELDS:
            raise NotFound()
        theme = request.env["login.theme"].sudo().browse(theme_id).exists()
        if not theme or not theme[field_name]:
            raise NotFound()
        can_preview = not request.env.user._is_public() and request.env.user.has_group(
            "atliis_login_theme_studio.group_login_theme_manager"
        )
        if not can_preview and not theme._is_theme_currently_active():
            raise NotFound()
        content = base64.b64decode(theme[field_name])
        return request.make_response(
            content,
            headers=[
                ("Content-Type", guess_mimetype(content, default="image/png")),
                ("Cache-Control", "public, max-age=3600"),
                ("X-Content-Type-Options", "nosniff"),
            ],
        )

    @http.route("/login_theme_studio/preview/<int:theme_id>/frame", type="http", auth="user")
    def preview_frame(self, theme_id, device="desktop", **kwargs):
        theme = self._get_preview_theme(theme_id)
        if device not in PREVIEW_DEVICES:
            device = "desktop"
        response = request.render(
            "atliis_login_theme_studio.login_theme_preview_frame",
            {
                "theme": theme,
                "login_theme_data": theme._get_safe_theme_values(),
                "preview_device": device,
            },
        )
        response.headers["X-Frame-Options"] = "SAMEORIGIN"
        return response
