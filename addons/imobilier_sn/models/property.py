import re
import unicodedata

from odoo import api, fields, models, _
from odoo.exceptions import ValidationError


class ImobilierSNProperty(models.Model):
    _name = "imobilier.sn.property"
    _description = "Produit immobilier"
    _inherit = ["mail.thread", "mail.activity.mixin"]
    _order = "id desc"

    name = fields.Char(
        string="Nom technique",
        compute="_compute_name",
        store=True,
        readonly=True,
        copy=False,
        tracking=True,
    )
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

    # Adresse formelle du Sénégal
    country_id = fields.Many2one(
        "res.country",
        string="Pays",
        default=lambda self: self.env["res.country"].search([("code", "=", "SN")], limit=1),
        readonly=True,
        ondelete="restrict",
    )
    region_id = fields.Many2one(
        "kiiraaye.geographie",
        string="Région",
        domain="[('country_id', '=', country_id), ('niveau', '=', 'niveau1')]",
        ondelete="restrict",
        tracking=True,
    )
    departement_id = fields.Many2one(
        "kiiraaye.geographie",
        string="Département",
        domain="[('country_id', '=', country_id), ('niveau', '=', 'niveau2'), ('parent_id', '=', region_id)]",
        ondelete="restrict",
        tracking=True,
    )
    arrondissement_id = fields.Many2one(
        "kiiraaye.geographie",
        string="Arrondissement",
        domain="[('country_id', '=', country_id), ('niveau', '=', 'localite'), ('designation_locale', '=', 'Arrondissement'), ('parent_id', '=', departement_id)]",
        ondelete="restrict",
        tracking=True,
    )
    commune_id = fields.Many2one(
        "kiiraaye.geographie",
        string="Commune",
        domain="[('country_id', '=', country_id), ('niveau', '=', 'niveau3'), ('parent_id', '=', departement_id)]",
        ondelete="restrict",
        tracking=True,
    )
    quartier_id = fields.Many2one(
        "kiiraaye.geographie",
        string="Quartier / Village",
        domain="[('country_id', '=', country_id), ('niveau', '=', 'niveau5'), ('parent_id', '=', commune_id)]",
        ondelete="restrict",
        tracking=True,
    )
    address_line = fields.Char(
        string="Adresse / Rue / Numéro",
        tracking=True,
        help="Rue, numéro, lot, villa, immeuble ou autre précision physique.",
    )
    location = fields.Char(
        string="Adresse complète",
        readonly=True,
        copy=False,
        tracking=True,
        help="Adresse générée automatiquement depuis le référentiel géographique du Sénégal.",
    )
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

    def _format_formal_location(self):
        self.ensure_one()
        parts = [
            self.address_line,
            self.quartier_id.name,
            self.commune_id.name,
            self.arrondissement_id.name,
            self.departement_id.name,
            self.region_id.name,
            self.country_id.name,
        ]
        return ", ".join(dict.fromkeys(
            part.strip()
            for part in parts
            if part and part.strip()
        ))

    def _sync_formal_location(self):
        for rec in self:
            if any((
                rec.region_id,
                rec.departement_id,
                rec.arrondissement_id,
                rec.commune_id,
                rec.quartier_id,
                rec.address_line,
            )):
                formatted = rec._format_formal_location()
                if rec.location != formatted:
                    rec.with_context(skip_formal_location_sync=True).write({
                        "location": formatted,
                    })

    @api.onchange("region_id")
    def _onchange_region_id(self):
        for rec in self:
            rec.departement_id = False
            rec.arrondissement_id = False
            rec.commune_id = False
            rec.quartier_id = False
            rec.location = rec._format_formal_location()

    @api.onchange("departement_id")
    def _onchange_departement_id(self):
        for rec in self:
            rec.arrondissement_id = False
            rec.commune_id = False
            rec.quartier_id = False
            rec.location = rec._format_formal_location()

    @api.onchange("commune_id")
    def _onchange_commune_id(self):
        for rec in self:
            rec.quartier_id = False
            rec.location = rec._format_formal_location()

    @api.onchange("arrondissement_id", "quartier_id", "address_line")
    def _onchange_formal_address(self):
        for rec in self:
            rec.location = rec._format_formal_location()

    @api.model_create_multi
    def create(self, vals_list):
        country = self.env["res.country"].search([("code", "=", "SN")], limit=1)
        for vals in vals_list:
            if not vals.get("country_id") and country:
                vals["country_id"] = country.id
        records = super().create(vals_list)
        records._sync_formal_location()
        return records

    def write(self, vals):
        address_fields = {
            "country_id",
            "region_id",
            "departement_id",
            "arrondissement_id",
            "commune_id",
            "quartier_id",
            "address_line",
        }
        res = super().write(vals)
        if not self.env.context.get("skip_formal_location_sync") and address_fields.intersection(vals):
            self._sync_formal_location()
        return res

    @api.constrains(
        "country_id",
        "region_id",
        "departement_id",
        "arrondissement_id",
        "commune_id",
        "quartier_id",
    )
    def _check_formal_senegal_address(self):
        for rec in self:
            if not any((rec.region_id, rec.departement_id, rec.commune_id)):
                # Tolérance pour les anciens produits créés avant la mise en place
                # du référentiel formel.
                continue
            if rec.country_id and rec.country_id.code != "SN":
                raise ValidationError(_("L'adresse formelle d'un produit doit être rattachée au Sénégal."))
            if rec.region_id and rec.region_id.niveau != "niveau1":
                raise ValidationError(_("La région sélectionnée est invalide."))
            if rec.departement_id and (
                rec.departement_id.niveau != "niveau2"
                or rec.departement_id.parent_id != rec.region_id
            ):
                raise ValidationError(_("Le département doit appartenir à la région sélectionnée."))
            if rec.arrondissement_id and (
                rec.arrondissement_id.niveau != "localite"
                or rec.arrondissement_id.designation_locale != "Arrondissement"
                or rec.arrondissement_id.parent_id != rec.departement_id
            ):
                raise ValidationError(_("L'arrondissement doit appartenir au département sélectionné."))
            if rec.commune_id and (
                rec.commune_id.niveau != "niveau3"
                or rec.commune_id.parent_id != rec.departement_id
            ):
                raise ValidationError(_("La commune doit appartenir au département sélectionné."))
            if rec.quartier_id and (
                rec.quartier_id.niveau != "niveau5"
                or rec.quartier_id.parent_id != rec.commune_id
            ):
                raise ValidationError(_("Le quartier / village doit appartenir à la commune sélectionnée."))

        for vals in vals_list:
            if not vals.get("sequence_number"):
                seq = self.env["ir.sequence"].next_by_code("imobilier.sn.property")
                vals["sequence_number"] = int(seq or "0")
        return super().create(vals_list)

    @api.depends(
        "property_type",
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
            if rec.property_type == "apartment":
                kind = rec._slug(rec.apartment_type or "APP")
                apartment_number = (
                    rec._slug(rec.apartment_number)
                    if rec.apartment_number
                    else number
                )
                rec.reference = f"APP-{kind}-{owner}-{location}-{apartment_number}"
            elif rec.property_type == "house":
                kind = rec._slug(rec.house_type or "R1")
                rec.reference = f"MAISON-{kind}-{owner}-{location}-{number}"
            elif rec.property_type == "shop":
                rec.reference = f"MAG-{owner}-{location}-{number}"
            elif rec.property_type == "land":
                rec.reference = f"TERRAIN-{owner}-{location}-{number}"
            else:
                rec.reference = f"IMMO-{number}"

    @api.depends("reference")
    def _compute_name(self):
        for rec in self:
            rec.name = rec.reference or "PRODUIT"

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
