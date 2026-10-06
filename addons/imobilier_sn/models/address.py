# -*- coding: utf-8 -*-
import logging
import json
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from odoo import api, fields, models, _
from odoo.exceptions import UserError, ValidationError

_logger = logging.getLogger(__name__)

GALSEN_API_BASE = "https://galsenapi.lassanasiby.com/api/v1"


class ImobilierSNAddress(models.Model):
    _name = "imobilier.sn.address"
    _description = "Référentiel d'adresses du Sénégal - Immobilier SN"
    _parent_name = "parent_id"
    _parent_store = True
    _rec_name = "name"
    _order = "level, name"

    name = fields.Char(string="Nom", required=True, index=True)
    code = fields.Char(string="Code", index=True)
    level = fields.Selection([
        ("region", "Région"),
        ("department", "Département"),
        ("arrondissement", "Arrondissement"),
        ("commune", "Commune"),
        ("locality", "Quartier / Village / Localité"),
    ], string="Niveau", required=True, index=True)
    parent_id = fields.Many2one(
        "imobilier.sn.address",
        string="Parent",
        index=True,
        ondelete="restrict",
    )
    parent_path = fields.Char(index=True)
    country_id = fields.Many2one(
        "res.country",
        string="Pays",
        required=True,
        default=lambda self: self.env["res.country"].search([("code", "=", "SN")], limit=1),
        ondelete="restrict",
        index=True,
    )
    source = fields.Char(string="Source")
    source_uid = fields.Char(string="Identifiant source", index=True)
    active = fields.Boolean(default=True)

    child_ids = fields.One2many(
        "imobilier.sn.address",
        "parent_id",
        string="Sous-zones",
    )

    _source_unique = models.Constraint(
        "UNIQUE(country_id, source_uid)",
        "L'identifiant source doit être unique pour un pays.",
    )

    @api.constrains("parent_id", "level", "country_id")
    def _check_hierarchy(self):
        ranks = {
            "region": 1,
            "department": 2,
            "arrondissement": 3,
            "commune": 4,
            "locality": 5,
        }
        for rec in self:
            if rec.country_id.code != "SN":
                raise ValidationError(_("Le référentiel Immobilier SN est réservé au Sénégal."))
            if rec.parent_id and rec.parent_id.country_id != rec.country_id:
                raise ValidationError(_("Une adresse doit appartenir au même pays que son parent."))
            if rec.parent_id and ranks.get(rec.level, 99) <= ranks.get(rec.parent_id.level, 99):
                raise ValidationError(_("La hiérarchie d'adresse est invalide."))

    @staticmethod
    def _api_get(endpoint, params=None):
        query = urlencode(params or {})
        url = f"{GALSEN_API_BASE}/{endpoint.strip('/')}/"
        if query:
            url = f"{url}?{query}"
        try:
            request = Request(
                url,
                headers={
                    "User-Agent": "Imobilier-SN/19.0",
                    "Accept": "application/json",
                },
            )
            with urlopen(request, timeout=60) as response:
                return json.loads(response.read().decode("utf-8"))
        except (HTTPError, URLError, TimeoutError, ValueError) as exc:
            raise UserError(
                _("Impossible de récupérer le référentiel d'adresses Sénégal depuis %s.\n\n%s")
                % (url, exc)
            )

    @classmethod
    def _api_get_all(cls, endpoint, params=None):
        results = []
        page = 1
        base_params = dict(params or {})
        while True:
            call_params = dict(base_params)
            call_params.update({"page": page, "page_size": 200})
            payload = cls._api_get(endpoint, call_params)
            rows = payload.get("results", []) if isinstance(payload, dict) else []
            results.extend(rows)
            if not isinstance(payload, dict) or not payload.get("next") or not rows:
                break
            page += 1
        return results

    @api.model
    def _upsert(self, source_uid, values):
        record = self.search([
            ("country_id", "=", values["country_id"]),
            ("source_uid", "=", source_uid),
        ], limit=1)
        values = dict(values)
        values["source_uid"] = source_uid
        if record:
            record.write(values)
            return record
        return self.create(values)

    @api.model
    def sync_administrative_reference(self):
        country = self.env["res.country"].search([("code", "=", "SN")], limit=1)
        if not country:
            raise UserError(_("Le pays Sénégal n'est pas configuré dans Odoo."))

        region_map = {}
        for item in self._api_get_all("regions"):
            pcode = item.get("pcode") or item.get("code_court")
            if not pcode:
                continue
            rec = self._upsert(
                f"GALSEN-REGION-{pcode}",
                {
                    "name": item.get("nom") or pcode,
                    "code": pcode,
                    "level": "region",
                    "parent_id": False,
                    "country_id": country.id,
                    "source": "GalsenAPI / données administratives Sénégal",
                    "active": True,
                },
            )
            region_map[pcode] = rec

        department_map = {}
        for item in self._api_get_all("departements"):
            pcode = item.get("pcode")
            parent = region_map.get(item.get("region"))
            if not pcode or not parent:
                continue
            rec = self._upsert(
                f"GALSEN-DEPT-{pcode}",
                {
                    "name": item.get("nom") or pcode,
                    "code": pcode,
                    "level": "department",
                    "parent_id": parent.id,
                    "country_id": country.id,
                    "source": "GalsenAPI / données administratives Sénégal",
                    "active": True,
                },
            )
            department_map[pcode] = rec

        arrondissement_map = {}
        for item in self._api_get_all("arrondissements"):
            pcode = item.get("pcode")
            parent = department_map.get(item.get("departement"))
            if not pcode or not parent:
                continue
            rec = self._upsert(
                f"GALSEN-ARR-{pcode}",
                {
                    "name": item.get("nom") or pcode,
                    "code": pcode,
                    "level": "arrondissement",
                    "parent_id": parent.id,
                    "country_id": country.id,
                    "source": "GalsenAPI / données administratives Sénégal",
                    "active": True,
                },
            )
            arrondissement_map[pcode] = rec

        commune_map = {}
        for item in self._api_get_all("communes"):
            item_id = item.get("id")
            parent = department_map.get(item.get("departement"))
            if item_id is None or not parent:
                continue
            rec = self._upsert(
                f"GALSEN-COMMUNE-{item_id}",
                {
                    "name": item.get("nom") or str(item_id),
                    "code": str(item_id),
                    "level": "commune",
                    "parent_id": parent.id,
                    "country_id": country.id,
                    "source": "GalsenAPI / données administratives Sénégal",
                    "active": True,
                },
            )
            commune_map[item_id] = rec

        return {
            "regions": len(region_map),
            "departments": len(department_map),
            "arrondissements": len(arrondissement_map),
            "communes": len(commune_map),
        }

    @api.model
    def sync_localities(self, max_pages=5):
        country = self.env["res.country"].search([("code", "=", "SN")], limit=1)
        if not country:
            raise UserError(_("Le pays Sénégal n'est pas configuré dans Odoo."))

        communes = {
            rec.code: rec
            for rec in self.search([
                ("country_id", "=", country.id),
                ("level", "=", "commune"),
                ("active", "=", True),
            ])
            if rec.code
        }

        page = 1
        created = updated = skipped = 0
        while page <= max_pages:
            payload = self._api_get(
                "villages",
                {"page": page, "page_size": 200},
            )
            rows = payload.get("results", []) if isinstance(payload, dict) else []
            if not rows:
                break

            for item in rows:
                village_id = item.get("id")
                name = (item.get("nom") or "").strip()
                commune_id = item.get("commune")
                if isinstance(commune_id, dict):
                    commune_id = commune_id.get("id")
                try:
                    commune_id = str(int(commune_id))
                except (TypeError, ValueError):
                    commune_id = ""
                parent = communes.get(commune_id)

                if not village_id or not name or not parent:
                    skipped += 1
                    continue

                source_uid = f"GALSEN-VILLAGE-{village_id}"
                existing = self.search([
                    ("country_id", "=", country.id),
                    ("source_uid", "=", source_uid),
                ], limit=1)
                values = {
                    "name": name,
                    "code": str(village_id),
                    "level": "locality",
                    "parent_id": parent.id,
                    "country_id": country.id,
                    "source": "GalsenAPI / Répertoire localités Sénégal",
                    "active": True,
                }
                if existing:
                    existing.write(values)
                    updated += 1
                else:
                    values["source_uid"] = source_uid
                    self.create(values)
                    created += 1

            if not payload.get("next"):
                break
            page += 1

        return {
            "created": created,
            "updated": updated,
            "skipped": skipped,
            "pages": page,
        }

    def action_sync_administrative_reference(self):
        result = self.sync_administrative_reference()
        self.env.cr.commit()
        return {
            "type": "ir.actions.client",
            "tag": "display_notification",
            "params": {
                "title": _("Référentiel Sénégal synchronisé"),
                "message": _(
                    "%s régions, %s départements, %s arrondissements et %s communes."
                ) % (
                    result["regions"],
                    result["departments"],
                    result["arrondissements"],
                    result["communes"],
                ),
                "type": "success",
                "sticky": False,
            },
        }

    def action_sync_localities(self):
        result = self.sync_localities(max_pages=10)
        self.env.cr.commit()
        return {
            "type": "ir.actions.client",
            "tag": "display_notification",
            "params": {
                "title": _("Localités synchronisées"),
                "message": _(
                    "%s créées, %s mises à jour, %s ignorées sur %s pages."
                ) % (
                    result["created"],
                    result["updated"],
                    result["skipped"],
                    result["pages"],
                ),
                "type": "success",
                "sticky": False,
            },
        }
