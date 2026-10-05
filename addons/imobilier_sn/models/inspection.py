from odoo import fields, models


class ImobilierSNInspection(models.Model):
    _name = "imobilier.sn.inspection"
    _description = "État des lieux"
    _inherit = ["mail.thread", "mail.activity.mixin"]
    _order = "inspection_date desc, id desc"

    name = fields.Char(
        string="Référence",
        default=lambda self: self.env["ir.sequence"].next_by_code("imobilier.sn.inspection") or "Nouveau",
        readonly=True,
        copy=False,
    )
    contract_id = fields.Many2one(
        "imobilier.sn.contract",
        string="Contrat",
        required=True,
        ondelete="cascade",
    )
    property_id = fields.Many2one(
        related="contract_id.property_id",
        string="Bien",
        store=True,
        readonly=True,
    )
    tenant_id = fields.Many2one(
        related="contract_id.customer_id",
        string="Locataire",
        store=True,
        readonly=True,
    )
    inspection_type = fields.Selection(
        [
            ("before", "Avant location"),
            ("after", "Après location"),
        ],
        string="Type d'état des lieux",
        required=True,
    )
    inspection_date = fields.Date(
        string="Date",
        default=fields.Date.context_today,
        required=True,
    )
    condition = fields.Selection(
        [
            ("excellent", "Excellent"),
            ("good", "Bon"),
            ("average", "Moyen"),
            ("bad", "Mauvais"),
        ],
        string="État général",
        default="good",
    )
    meter_electricity = fields.Char(string="Compteur électricité")
    meter_water = fields.Char(string="Compteur eau")
    keys_count = fields.Integer(string="Nombre de clés")
    description = fields.Text(string="Description / constat")
    attachment = fields.Binary(string="Photos / document")
    attachment_filename = fields.Char(string="Nom du fichier")
