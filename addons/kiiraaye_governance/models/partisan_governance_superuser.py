from odoo import models


class KiiraayePartisanGovernanceSuperuser(models.Model):
    _inherit = "kiiraaye.partisan"

    def _apply_coordinator_scope_on_create(self, vals):
        if self.env.is_superuser():
            return
        return super()._apply_coordinator_scope_on_create(vals)

    def _check_coordinator_scope_on_write(self, vals):
        if self.env.is_superuser():
            return
        return super()._check_coordinator_scope_on_write(vals)
