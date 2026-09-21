from odoo import fields, models


class ResUsers(models.Model):
    _inherit = "res.users"

    @property
    def SELF_READABLE_FIELDS(self):
        return super().SELF_READABLE_FIELDS + ["sidebar_type"]

    @property
    def SELF_WRITEABLE_FIELDS(self):
        return super().SELF_WRITEABLE_FIELDS + ["sidebar_type"]

    sidebar_type = fields.Selection(
        [
            ("invisible", "Invisible"),
            ("small", "Small"),
            ("large", "Large"),
        ],
        string="Sidebar Type",
        default="large",
        required=True,
    )
