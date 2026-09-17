# -*- coding: utf-8 -*-
import logging

from odoo import fields, models, _
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)

_GALSEN_API_BASE = "https://galsenapi.lassanasiby.com/api/v1"


class ResCountrySenegalGeography(models.Model):
    _inherit = "res.country"

    @staticmethod
    def _galsen_get(url, params=None):
        import json
        from urllib.error import HTTPError, URLError
        from urllib.parse import urlencode
        from urllib.request import Request, urlopen

        query = urlencode(params or {})
        full_url = f"{url}?{query}" if query else url
        try:
            request = Request(
                full_url,
                headers={
                    "User-Agent": "Kiiraaye-Gouvernance/19.0",
                    "Accept": "application/json",
                },
            )
            with urlopen(request, timeout=60) as response:
                return json.loads(response.read().decode("utf-8"))
        except (HTTPError, URLError, TimeoutError, ValueError) as exc:
            raise UserError(
                _("Impossible de récupérer le référentiel géographique du Sénégal depuis %s.\n\n%s")
                % (full_url, exc)
            )

    @classmethod
    def _galsen_get_all(cls, endpoint):
        results = []
        page = 1
        while True:
            payload = cls._galsen_get(
                f"{_GALSEN_API_BASE}/{endpoint}/",
                {"page": page, "page_size": 200},
            )
            page_results = payload.get("results", []) if isinstance(payload, dict) else []
            results.extend(page_results)
            next_url = payload.get("next") if isinstance(payload, dict) else None
            if not next_url or not page_results:
                break
            page += 1
        return results

    def _ensure_senegal_root(self):
        self.ensure_one()
        Geo = self.env["kiiraaye.geographie"].sudo()
        root = Geo.search(
            [("country_id", "=", self.id), ("niveau", "=", "pays")],
            limit=1,
        )
        if not root:
            root = Geo.create(
                {
                    "name": self.name,
                    "code": self.code,
                    "country_id": self.id,
                    "niveau": "pays",
                    "source": "GalsenAPI / Odoo",
                    "source_uid": "GALSEN-COUNTRY-SN",
                    "source_admin_level": "MANUAL",
                    "active": True,
                }
            )
        return root

    def _upsert_senegal_geo(self, source_uid, values):
        Geo = self.env["kiiraaye.geographie"].sudo()
        record = Geo.search(
            [("country_id", "=", self.id), ("source_uid", "=", source_uid)],
            limit=1,
        )
        if record:
            record.write(values)
        else:
            values["source_uid"] = source_uid
            record = Geo.create(values)
        return record

    def _load_senegal_regions(self, root):
        records = {}
        for item in self._galsen_get_all("regions"):
            pcode = item.get("pcode")
            if not pcode:
                continue
            records[pcode] = self._upsert_senegal_geo(
                f"GALSEN-REGION-{pcode}",
                {
                    "name": item.get("nom") or pcode,
                    "code": item.get("code_court") or pcode,
                    "country_id": self.id,
                    "parent_id": root.id,
                    "niveau": "niveau1",
                    "source_admin_level": "MANUAL",
                    "designation_locale": "Région",
                    "source": "GalsenAPI (HDX/OCHA, ANSD)",
                    "source_url": f"{_GALSEN_API_BASE}/regions/{pcode}/",
                    "active": True,
                },
            )
        return records

    def _load_senegal_departments(self, regions):
        records = {}
        for item in self._galsen_get_all("departements"):
            pcode = item.get("pcode")
            parent = regions.get(item.get("region"))
            if not pcode or not parent:
                continue
            records[pcode] = self._upsert_senegal_geo(
                f"GALSEN-DEPT-{pcode}",
                {
                    "name": item.get("nom") or pcode,
                    "code": pcode,
                    "country_id": self.id,
                    "parent_id": parent.id,
                    "niveau": "niveau2",
                    "source_admin_level": "MANUAL",
                    "designation_locale": "Département",
                    "source": "GalsenAPI (HDX/OCHA, ANSD)",
                    "source_url": f"{_GALSEN_API_BASE}/departements/{pcode}/",
                    "active": True,
                },
            )
        return records

    def _load_senegal_arrondissements(self, departments):
        records = {}
        for item in self._galsen_get_all("arrondissements"):
            pcode = item.get("pcode")
            parent = departments.get(item.get("departement"))
            if not pcode or not parent:
                continue
            # L'arrondissement est conservé comme unité locale administrative
            # attachée au département. On évite de lui attribuer niveau3 afin
            # de réserver niveau3 à la commune utilisée par les sections.
            records[pcode] = self._upsert_senegal_geo(
                f"GALSEN-ARR-{pcode}",
                {
                    "name": item.get("nom") or pcode,
                    "code": pcode,
                    "country_id": self.id,
                    "parent_id": parent.id,
                    "niveau": "localite",
                    "source_admin_level": "MANUAL",
                    "designation_locale": "Arrondissement",
                    "source": "GalsenAPI (HDX/OCHA, ANSD)",
                    "source_url": f"{_GALSEN_API_BASE}/arrondissements/{pcode}/",
                    "active": True,
                },
            )
        return records

    def _load_senegal_communes(self, departments):
        records = {}
        for item in self._galsen_get_all("communes"):
            item_id = item.get("id")
            parent = departments.get(item.get("departement"))
            if item_id is None or not parent:
                continue
            records[item_id] = self._upsert_senegal_geo(
                f"GALSEN-COMMUNE-{item_id}",
                {
                    "name": item.get("nom") or str(item_id),
                    "code": str(item_id),
                    "country_id": self.id,
                    "parent_id": parent.id,
                    "niveau": "niveau3",
                    "source_admin_level": "MANUAL",
                    "designation_locale": item.get("type") or "Commune",
                    "source": "GalsenAPI (HDX/OCHA, ANSD)",
                    "source_url": f"{_GALSEN_API_BASE}/communes/{item_id}/",
                    "active": True,
                },
            )
        return records

    def _load_senegal_villages(self, regions, communes):
        count = 0
        for item in self._galsen_get_all("villages"):
            item_id = item.get("id")
            if item_id is None:
                continue
            parent = communes.get(item.get("commune")) or regions.get(item.get("region"))
            if not parent:
                continue
            self._upsert_senegal_geo(
                f"GALSEN-VILLAGE-{item_id}",
                {
                    "name": item.get("nom") or str(item_id),
                    "code": str(item_id),
                    "country_id": self.id,
                    "parent_id": parent.id,
                    "niveau": "niveau5",
                    "source_admin_level": "MANUAL",
                    "designation_locale": "Village / localité",
                    "source": "GalsenAPI (HDX/OCHA, ANSD)",
                    "source_url": f"{_GALSEN_API_BASE}/villages/{item_id}/",
                    "active": True,
                },
            )
            count += 1
        return count

    def action_load_senegal_default_geography(self):
        self.ensure_one()
        if self.code != "SN":
            raise UserError(_("Cette opération est réservée au Sénégal."))

        root = self._ensure_senegal_root()
        regions = self._load_senegal_regions(root)
        departments = self._load_senegal_departments(regions)
        arrondissements = self._load_senegal_arrondissements(departments)
        communes = self._load_senegal_communes(departments)
        villages_count = self._load_senegal_villages(regions, communes)

        self.sudo().write({
            "kiiraaye_geo_source": "galsenapi",
            "kiiraaye_iso3": "SEN",
            "kiiraaye_geo_region_level": "niveau1",
            "kiiraaye_geo_department_level": "niveau2",
            "kiiraaye_geo_commune_level": "niveau3",
            "kiiraaye_geo_quartier_level": "niveau5",
            "kiiraaye_geo_region_label": "Région",
            "kiiraaye_geo_department_label": "Département",
            "kiiraaye_geo_commune_label": "Commune",
            "kiiraaye_geo_quartier_label": "Quartier / Village / Localité",
            "kiiraaye_geo_status": "ok",
            "kiiraaye_geo_last_sync": fields.Datetime.now(),
            "kiiraaye_geo_message": (
                "Référentiel Sénégal chargé automatiquement depuis GalsenAPI : "
                f"{len(regions)} régions, {len(departments)} départements, "
                f"{len(arrondissements)} arrondissements, {len(communes)} communes, "
                f"{villages_count} villages/localités."
            ),
        })

        return {
            "type": "ir.actions.client",
            "tag": "display_notification",
            "params": {
                "title": _("Référentiel Sénégal chargé"),
                "message": self.kiiraaye_geo_message,
                "type": "success",
                "sticky": False,
            },
        }

    def action_sync_kiiraaye_geography(self):
        if self.ensure_one().code == "SN":
            return self.action_load_senegal_default_geography()
        return super().action_sync_kiiraaye_geography()
