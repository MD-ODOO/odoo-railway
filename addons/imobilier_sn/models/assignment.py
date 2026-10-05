from odoo import api, fields, models


class ImobilierSNAssignment(models.Model):
    _name = "imobilier.sn.assignment"
    _description = "Affectation d'un bien à un courtier"
    _order = "id desc"

    name = fields.Char(
        string="Référence",
        default=lambda self: self.env["ir.sequence"].next_by_code("imobilier.sn.assignment") or "Nouveau",
        readonly=True,
        copy=False,
    )
    property_id = fields.Many2one(
        "imobilier.sn.property",
        string="Bien immobilier",
        required=True,
        ondelete="cascade",
    )
    broker_id = fields.Many2one(
        "res.partner",
        string="Courtier",
        required=True,
        domain=[("is_imobilier_broker", "=", True)],
        ondelete="restrict",
    )
    commission_percent = fields.Float(
        string="Commission (%)",
        required=True,
        related="broker_id.broker_commission_percent",
        readonly=False,
    )
    commission_amount = fields.Monetary(
        string="Commission estimée",
        compute="_compute_commission_amount",
        store=True,
        currency_field="currency_id",
    )
    currency_id = fields.Many2one(
        related="property_id.currency_id",
        string="Devise",
        readonly=True,
    )
    date_assigned = fields.Date(
        string="Date d'affectation",
        default=fields.Date.context_today,
        required=True,
    )
    state = fields.Selection(
        [("active", "Active"), ("closed", "Clôturée"), ("cancelled", "Annulée")],
        default="active",
        string="État",
    )
    note = fields.Text(string="Note")

    @api.depends("property_id.price", "property_id.rental_price", "commission_percent")
    def _compute_commission_amount(self):
        for rec in self:
            base = rec.property_id.price or rec.property_id.rental_price or 0
            rec.commission_amount = base * (rec.commission_percent or 0) / 100
