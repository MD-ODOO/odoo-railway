import re
import unicodedata

from odoo import api, fields, models, _
from odoo.exceptions import ValidationError


class ImobilierSNProperty(models.Model):
    _name = "imobilier.sn.property"
    _description = "Bien immobilier"
    _inherit = ["mail.thread", "mail.activity.mixin"]
    _order = "id desc"

    name = fields.Char(string="Nom du bien", required=True, tracking=True)
    reference = fields.Char(
        string="Référence",
        compute="_compute_reference",
        store=True,
        readonly=True,
        copy=False,
        tracking=True,
    )
    sequence_number = fields.Integer(string="Numéro", readonly=True, copy=False)

    property_type = fields.Selection(
        [
            ("apartment", "Appartement"),
            ("house", "Maison entière"),
            ("shop", "Magasin"),
            ("land", "Terrain"),
        ],
        string="Type de produit",
        required=True,
        tracking=True,
    )
    status = fields.Selection(
        [
            ("available", "Disponible"),
            ("reserved", "Réservé"),
            ("rented", "Loué"),
            ("sold", "Vendu"),
            ("unavailable", "Indisponible"),
        ],
        string="État",
        default="available",
        tracking=True,
    )

    owner_id = fields.Many2one(
        "res.partner",
        string="Propriétaire",
        required=True,
        tracking=True,
        ondelete="restrict",
    )
    location = fields.Char(string="Localisation", required=True, tracking=True)
    description = fields.Text(string="Description")

    currency_id = fields.Many2one(
        "res.currency",
        string="Devise",
        default=lambda self: self.env.company.currency_id,
        required=True,
    )
    price = fields.Monetary(string="Prix", currency_field="currency_id")
    rental_price = fields.Monetary(
        string="Prix de location",
        currency_field="currency_id",
    )
    security_deposit = fields.Monetary(
        string="Caution",
        currency_field="currency_id",
        help="Montant de la caution demandé pour une location.",
    )
    rental_advance_count = fields.Float(
        string="Nombre de mois d'avance",
        default=0,
        help="Nombre de mois de loyer à payer avant l'entrée dans le bien.",
    )

    # Appartement
    apartment_type = fields.Char(
        string="Type d'appartement",
        help="Exemples : Studio, Studio américain, 2CS, 3CS, 4CS, 5CS. Champ volontairement libre.",
    )
    apartment_number = fields.Char(
        string="Numéro d'appartement",
        help="Numéro interne de l'appartement chez le propriétaire.",
    )

    # Maison entière
    house_type = fields.Char(
        string="Type de maison",
        help="Exemples : R1, R2, R3, R5. Champ volontairement libre.",
    )
    paper_type = fields.Char(
        string="Type de papier",
        help="Exemples : Bail, Titre foncier, etc. Champ libre pour s'adapter au dossier.",
    )
    payment_mode = fields.Char(
        string="Modalité de paiement",
        help="Champ libre pour préciser la modalité convenue.",
    )
    house_unit_ids = fields.One2many(
        "imobilier.sn.house.unit",
        "property_id",
        string="Répartition des appartements",
    )

    # Magasin
    shop_deposit = fields.Monetary(
        string="Montant caution magasin",
        currency_field="currency_id",
    )
    desired_activity = fields.Char(string="Activité souhaitée")

    # Terrain
    land_area = fields.Float(string="Superficie")
    land_area_unit = fields.Selection(
        [
            ("m2", "m²"),
            ("ha", "Hectare"),
            ("a", "Are"),
        ],
        string="Unité superficie",
        default="m2",
    )

    assignment_ids = fields.One2many(
        "imobilier.sn.assignment",
        "property_id",
        string="Affectations courtiers",
    )
    contract_ids = fields.One2many(
        "imobilier.sn.contract",
        "property_id",
        string="Contrats",
    )
    inspection_ids = fields.One2many(
        "imobilier.sn.inspection",
        "property_id",
        string="États des lieux",
    )
    contract_count = fields.Integer(
        string="Contrats",
        compute="_compute_counts",
    )
    assignment_count = fields.Integer(
        string="Courtiers",
        compute="_compute_counts",
    )

    active = fields.Boolean(default=True)

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if not vals.get("sequence_number"):
                seq = self.env["ir.sequence"].next_by_code("imobilier.sn.property")
                vals["sequence_number"] = int(seq or "0")
        return super().create(vals_list)

    @api.depends(
        "property_type",
        "name",
        "owner_id.name",
        "location",
        "apartment_type",
        "house_type",
        "sequence_number",
    )
    def _compute_reference(self):
        for rec in self:
            number = str(rec.sequence_number or 0).zfill(4)
            location = rec._slug(rec.location or "LOCALISATION")
            owner = rec._slug(rec.owner_id.name or "PROPRIETAIRE")
            property_name = rec._slug(rec.name or "BIEN")
            if rec.property_type == "apartment":
                kind = rec._slug(rec.apartment_type or "APP")
                rec.reference = f"APP-{kind}-{property_name}-{location}-{number}"
            elif rec.property_type == "house":
                kind = rec._slug(rec.house_type or "R1")
                rec.reference = f"MAISON-{kind}-{owner}-{location}-{number}"
            elif rec.property_type == "shop":
                rec.reference = f"MAG-{owner}-{location}-{number}"
            elif rec.property_type == "land":
                rec.reference = f"TERRAIN-{owner}-{location}-{number}"
            else:
                rec.reference = f"IMMO-{number}"

    @api.depends("contract_ids", "assignment_ids")
    def _compute_counts(self):
        for rec in self:
            rec.contract_count = len(rec.contract_ids)
            rec.assignment_count = len(rec.assignment_ids)

    @staticmethod
    def _slug(value):
        value = unicodedata.normalize("NFKD", value).encode("ascii", "ignore").decode()
        value = re.sub(r"[^A-Za-z0-9]+", "-", value).strip("-")
        return value.upper()[:30] or "NA"

    @api.onchange("property_type")
    def _onchange_property_type(self):
        if self.property_type != "apartment":
            self.apartment_type = False
            self.apartment_number = False
        if self.property_type != "house":
            self.house_type = False
            self.paper_type = False
            self.payment_mode = False
            self.house_unit_ids = [(5, 0, 0)]
        if self.property_type != "shop":
            self.shop_deposit = 0
            self.desired_activity = False
        if self.property_type != "land":
            self.land_area = 0
            self.land_area_unit = "m2"

    def action_open_contracts(self):
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "name": _("Contrats"),
            "res_model": "imobilier.sn.contract",
            "view_mode": "list,form",
            "domain": [("property_id", "=", self.id)],
            "context": {"default_property_id": self.id},
        }

    def action_open_assignments(self):
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "name": _("Affectations courtiers"),
            "res_model": "imobilier.sn.assignment",
            "view_mode": "list,form",
            "domain": [("property_id", "=", self.id)],
            "context": {"default_property_id": self.id},
        }

    def action_mark_available(self):
        self.write({"status": "available"})
        return True

    def action_mark_reserved(self):
        self.write({"status": "reserved"})
        return True


class ImobilierSNHouseUnit(models.Model):
    _name = "imobilier.sn.house.unit"
    _description = "Répartition des appartements d'une maison"
    _order = "id"

    property_id = fields.Many2one(
        "imobilier.sn.property",
        string="Maison",
        required=True,
        ondelete="cascade",
    )
    apartment_type = fields.Char(
        string="Type appartement",
        required=True,
        help="Exemples : Studio américain, 2CS, 3CS, 4CS, 5CS.",
    )
    quantity = fields.Integer(string="Nombre", required=True, default=1)
    note = fields.Char(string="Note")

    @api.constrains("quantity")
    def _check_quantity(self):
        for line in self:
            if line.quantity < 1:
                raise ValidationError(_("Le nombre d'appartements doit être supérieur ou égal à 1."))
