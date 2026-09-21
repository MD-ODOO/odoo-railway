from odoo import models


class IrHttp(models.AbstractModel):
    _inherit = "ir.http"

    def session_info(self):
        result = super().session_info()
        if self.env.user._is_internal():
            for company in self.env.user.company_ids.with_context(bin_size=True):
                result["user_companies"]["allowed_companies"][company.id].update({
                    "has_appsbar_image": bool(company.appbar_image),
                    "appbar_background_color": company.appbar_background_color or "#172033",
                })
        return result
