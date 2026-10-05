from odoo import api, fields, models


class ResPartner(models.Model):
    _inherit = "res.partner"

    is_imobilier_broker = fields.Boolean(string="Est un courtier immobilier")
    broker_commission_percent = fields.Float(string="Commission courtier (%)", default=0)
    is_imobilier_tenant = fields.Boolean(string="Locataire immobilier")

    imobilier_property_ids = fields.One2many(
        "imobilier.sn.property",
        "owner_id",
        string="Biens immobiliers",
    )
    imobilier_apartment_count = fields.Integer(
        string="Appartements",
        compute="_compute_imobilier_counts",
    )
    imobilier_house_count = fields.Integer(
        string="Maisons",
        compute="_compute_imobilier_counts",
    )
    imobilier_shop_count = fields.Integer(
        string="Magasins",
        compute="_compute_imobilier_counts",
    )
    imobilier_land_count = fields.Integer(
        string="Terrains",
        compute="_compute_imobilier_counts",
    )
    imobilier_total_count = fields.Integer(
        string="Total biens",
        compute="_compute_imobilier_counts",
    )
    imobilier_broker_assignment_count = fields.Integer(
        string="Affectations courtier",
        compute="_compute_imobilier_counts",
    )

    @api.depends("imobilier_property_ids", "imobilier_property_ids.property_type")
    def _compute_imobilier_counts(self):
        for partner in self:
            properties = partner.imobilier_property_ids
            partner.imobilier_apartment_count = sum(p.property_type == "apartment" for p in properties)
            partner.imobilier_house_count = sum(p.property_type == "house" for p in properties)
            partner.imobilier_shop_count = sum(p.property_type == "shop" for p in properties)
            partner.imobilier_land_count = sum(p.property_type == "land" for p in properties)
            partner.imobilier_total_count = len(properties)
            partner.imobilier_broker_assignment_count = self.env[
                "imobilier.sn.assignment"
            ].search_count([("broker_id", "=", partner.id)])

    def _action_imobilier_properties(self, property_type=False):
        self.ensure_one()
        domain = [("owner_id", "=", self.id)]
        if property_type:
            domain.append(("property_type", "=", property_type))
        return {
            "type": "ir.actions.act_window",
            "name": "Biens immobiliers",
            "res_model": "imobilier.sn.property",
            "view_mode": "list,form",
            "domain": domain,
            "context": {"default_owner_id": self.id},
        }

    def action_imobilier_apartments(self):
        return self._action_imobilier_properties("apartment")

    def action_imobilier_houses(self):
        return self._action_imobilier_properties("house")

    def action_imobilier_shops(self):
        return self._action_imobilier_properties("shop")

    def action_imobilier_lands(self):
        return self._action_imobilier_properties("land")

    def action_imobilier_all_properties(self):
        return self._action_imobilier_properties()

    def action_imobilier_broker_assignments(self):
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "name": "Affectations de courtage",
            "res_model": "imobilier.sn.assignment",
            "view_mode": "list,form",
            "domain": [("broker_id", "=", self.id)],
            "context": {"default_broker_id": self.id},
        }
