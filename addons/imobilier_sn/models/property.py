# -*- coding: utf-8 -*-
import html
import json
import logging
import re
import unicodedata
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from odoo import api, fields, models, _
from odoo.exceptions import UserError, ValidationError


_logger = logging.getLogger(__name__)

NOMINATIM_URL = "https://nominatim.openstreetmap.org/search"


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

    # Adresse libre : aucune hiérarchie Odoo n'est imposée.
    location = fields.Char(
        string="Adresse de localisation",
        required=True,
        tracking=True,
        help=(
            "Saisissez directement l'adresse du produit : rue, quartier, "
            "immeuble, villa, lieu-dit, commune, etc."
        ),
    )
    region_name = fields.Char(
        string="Région",
        readonly=True,
        tracking=True,
        help="Région déterminée automatiquement par la géolocalisation.",
    )
    department_name = fields.Char(
        string="Département",
        readonly=True,
        tracking=True,
        help="Département déterminé automatiquement par la géolocalisation.",
    )
    geocoded_address = fields.Char(
        string="Adresse géocodée",
        readonly=True,
        copy=False,
    )
    latitude = fields.Float(
        string="Latitude",
        digits=(10, 7),
        readonly=True,
        copy=False,
    )
    longitude = fields.Float(
        string="Longitude",
        digits=(10, 7),
        readonly=True,
        copy=False,
    )
    map_embed_html = fields.Html(
        string="Carte",
        compute="_compute_map_embed",
        sanitize=False,
    )

    currency_id = fields.Many2one(
        "res.currency",
        string="Devise",
        default=lambda self: self.env.company.currency_id,
        required=True,
    )
    price = fields.Monetary(
        string="Prix / Loyer mensuel",
        currency_field="currency_id",
        help=(
            "Prix du produit. Pour un produit destiné à la location, "
            "ce montant correspond au loyer mensuel."
        ),
    )
    security_deposit_months = fields.Float(
        string="Nombre de mois de caution",
        default=0,
        help="La caution est calculée automatiquement : Prix × nombre de mois.",
    )
    security_deposit = fields.Monetary(
        string="Caution",
        currency_field="currency_id",
        compute="_compute_security_deposit",
        store=True,
        readonly=True,
        help="Calcul automatique : Prix × nombre de mois de caution.",
    )
    rental_advance_count = fields.Float(
        string="Nombre de mois d'avance",
        default=0,
        help="Nombre de mois de loyer à payer avant l'entrée dans le produit.",
    )
    payment_term_id = fields.Many2one(
        "account.payment.term",
        string="Modalité de paiement",
        domain="[('active', '=', True)]",
        tracking=True,
        help="Terme de paiement provenant directement du module Facturation.",
    )

    # Appartement
    apartment_type_id = fields.Many2one(
        "imobilier.sn.property.type",
        string="Type d'appartement",
        domain="[('category', '=', 'apartment'), ('active', '=', True)]",
        ondelete="restrict",
        tracking=True,
    )
    apartment_number = fields.Char(
        string="Numéro d'appartement",
        help="Numéro interne de l'appartement chez le propriétaire.",
    )

    # Maison entière
    house_type_id = fields.Many2one(
        "imobilier.sn.property.type",
        string="Type de maison",
        domain="[('category', '=', 'house'), ('active', '=', True)]",
        ondelete="restrict",
        tracking=True,
    )
    paper_type_id = fields.Many2one(
        "imobilier.sn.property.type",
        string="Type de papier",
        domain="[('category', '=', 'paper'), ('active', '=', True)]",
        ondelete="restrict",
        tracking=True,
    )
    house_unit_ids = fields.One2many(
        "imobilier.sn.house.unit",
        "property_id",
        string="Répartition des appartements",
    )

    # Magasin
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

    @api.depends("price", "security_deposit_months", "property_type")
    def _compute_security_deposit(self):
        for rec in self:
            if rec.property_type in ("apartment", "house", "shop"):
                rec.security_deposit = max(rec.price or 0, 0) * max(
                    rec.security_deposit_months or 0, 0
                )
            else:
                rec.security_deposit = 0

    @api.depends("latitude", "longitude")
    def _compute_map_embed(self):
        for rec in self:
            if not rec.latitude or not rec.longitude:
                rec.map_embed_html = False
                continue

            lat = rec.latitude
            lon = rec.longitude
            delta = 0.015
            bbox = ",".join([
                f"{lon - delta:.7f}",
                f"{lat - delta:.7f}",
                f"{lon + delta:.7f}",
                f"{lat + delta:.7f}",
            ])
            src = (
                "https://www.openstreetmap.org/export/embed.html?"
                + urlencode({
                    "bbox": bbox,
                    "layer": "mapnik",
                    "marker": f"{lat:.7f},{lon:.7f}",
                })
            )
            safe_src = html.escape(src, quote=True)
            rec.map_embed_html = (
                '<div style="width:100%; min-height:420px;">'
                f'<iframe src="{safe_src}" '
                'style="width:100%; height:420px; border:1px solid #ddd; border-radius:8px;" '
                'loading="lazy" title="Carte de localisation" referrerpolicy="no-referrer-when-downgrade">'
                '</iframe>'
                '</div>'
            )

    @staticmethod
    def _first_address_value(address, keys):
        for key in keys:
            value = address.get(key)
            if value:
                return value.strip()
        return False

    def action_geocode_address(self):
        for rec in self:
            rec._geocode_address()
        return True

    def _geocode_address(self):
        self.ensure_one()
        if not self.location or not self.location.strip():
            raise UserError(_("Veuillez renseigner l'adresse de localisation."))

        query = self.location.strip()
        if "senegal" not in query.lower() and "sénégal" not in query.lower():
            query = f"{query}, Sénégal"

        params = {
            "q": query,
            "format": "jsonv2",
            "addressdetails": 1,
            "limit": 1,
            "accept-language": "fr",
        }
        url = f"{NOMINATIM_URL}?{urlencode(params)}"

        try:
            request = Request(
                url,
                headers={
                    "User-Agent": "Imobilier-SN/19.0 (geocoding)",
                    "Accept": "application/json",
                },
            )
            with urlopen(request, timeout=20) as response:
                results = json.loads(response.read().decode("utf-8"))
        except (HTTPError, URLError, TimeoutError, ValueError) as exc:
            _logger.exception("Erreur de géocodage de l'adresse %s", self.location)
            raise UserError(
                _("La localisation n'a pas pu être déterminée. Vérifiez l'adresse puis réessayez.\n\n%s")
                % exc
            ) from exc

        if not results:
            raise UserError(
                _("Aucune localisation n'a été trouvée pour : %s") % self.location
            )

        result = results[0]
        address = result.get("address") or {}

        region = self._first_address_value(
            address,
            ("state", "region", "province", "state_district"),
        )
        department = self._first_address_value(
            address,
            ("county", "department", "state_district", "district", "city_district"),
        )

        try:
            latitude = float(result.get("lat"))
            longitude = float(result.get("lon"))
        except (TypeError, ValueError) as exc:
            raise UserError(_("Le service de cartographie n'a pas fourni de coordonnées valides.")) from exc

        self.write({
            "latitude": latitude,
            "longitude": longitude,
            "region_name": region or False,
            "department_name": department or False,
            "geocoded_address": result.get("display_name") or self.location,
        })

        message_parts = [_("Adresse géolocalisée.")]
        if region:
            message_parts.append(_("Région : %s") % region)
        if department:
            message_parts.append(_("Département : %s") % department)

        self.env["bus.bus"]._sendone(
            self.env.user.partner_id,
            "simple_notification",
            {
                "title": _("Géolocalisation"),
                "message": " — ".join(message_parts),
                "type": "success",
                "sticky": False,
            },
        )
        return True

    def action_open_google_maps(self):
        self.ensure_one()
        if not self.latitude or not self.longitude:
            self._geocode_address()
        return {
            "type": "ir.actions.act_url",
            "url": (
                "https://www.google.com/maps/search/?api=1&query=%s,%s"
                % (self.latitude, self.longitude)
            ),
            "target": "new",
        }

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if not vals.get("sequence_number"):
                seq = self.env["ir.sequence"].next_by_code("imobilier.sn.property")
                vals["sequence_number"] = int(seq or "0")
        return super().create(vals_list)

    def write(self, vals):
        res = super().write(vals)
        if "property_type" in vals and vals["property_type"] == "land":
            self.filtered(lambda r: r.property_type == "land").with_context(
                skip_land_cleanup=True
            ).write({
                "security_deposit_months": 0,
                "rental_advance_count": 0,
            })
        return res

    @api.constrains("price", "security_deposit_months", "rental_advance_count")
    def _check_financial_values(self):
        for rec in self:
            if rec.price < 0:
                raise ValidationError(_("Le prix ne peut pas être négatif."))
            if rec.security_deposit_months < 0:
                raise ValidationError(_("Le nombre de mois de caution ne peut pas être négatif."))
            if rec.rental_advance_count < 0:
                raise ValidationError(_("Le nombre de mois d'avance ne peut pas être négatif."))

    @api.depends(
        "property_type",
        "owner_id.name",
        "location",
        "apartment_type_id.name",
        "house_type_id.name",
        "sequence_number",
    )
    def _compute_reference(self):
        for rec in self:
            number = str(rec.sequence_number or 0).zfill(4)
            location = rec._slug(rec.location or "LOCALISATION")
            owner = rec._slug(rec.owner_id.name or "PROPRIETAIRE")
            if rec.property_type == "apartment":
                kind = rec._slug(rec.apartment_type_id.name or "APP")
                apartment_number = (
                    rec._slug(rec.apartment_number)
                    if rec.apartment_number
                    else number
                )
                rec.reference = f"APP-{kind}-{owner}-{location}-{apartment_number}"
            elif rec.property_type == "house":
                kind = rec._slug(rec.house_type_id.name or "R1")
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
            self.apartment_type_id = False
            self.apartment_number = False
        if self.property_type != "house":
            self.house_type_id = False
            self.paper_type_id = False
            self.house_unit_ids = [(5, 0, 0)]
        if self.property_type != "shop":
            self.desired_activity = False
        if self.property_type == "land":
            self.security_deposit_months = 0
            self.rental_advance_count = 0
        if self.property_type not in ("apartment", "house", "shop"):
            self.security_deposit_months = 0

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
    apartment_type_id = fields.Many2one(
        "imobilier.sn.property.type",
        string="Type appartement",
        required=True,
        domain="[('category', '=', 'apartment'), ('active', '=', True)]",
        ondelete="restrict",
    )
    quantity = fields.Integer(string="Nombre", required=True, default=1)
    note = fields.Char(string="Note")

    @api.constrains("quantity")
    def _check_quantity(self):
        for line in self:
            if line.quantity < 1:
                raise ValidationError(_("Le nombre d'appartements doit être supérieur ou égal à 1."))
