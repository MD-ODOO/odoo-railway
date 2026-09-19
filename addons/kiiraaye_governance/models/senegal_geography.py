# -*- coding: utf-8 -*-
import logging

from odoo import fields, models, _
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)

_GALSEN_API_BASE = "https://galsenapi.lassanasiby.com/api/v1"

class ResCountrySenegalGeography(models.Model):
    _inherit = "res.country"

    kiiraaye_geo_village_page = fields.Integer(
        string="Lots de localités ANSD",
        default=0,
        readonly=True,
        copy=False,
        help="Dernier lot de localités ANSD traité avec succès.",
    )
    kiiraaye_geo_village_loaded = fields.Integer(
        string="Villages / unités locales chargés",
        default=0,
        readonly=True,
        copy=False,
    )

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
                    "source_admin_level": "ADM1",
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
                    "source_admin_level": "ADM2",
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

    def _load_senegal_villages_galsen(
        self, communes, page_size=200, limit=None, start_page=1, max_pages=None
    ):
        """Charge les villages GalsenAPI par pages et écrit chaque page en lot."""
        Geo = self.env["kiiraaye.geographie"].sudo()
        loaded = 0
        updated = 0
        skipped = 0
        scanned = 0
        page = max(1, int(start_page or 1))
        pages_processed = 0
        target = int(limit) if limit else None

        while True:
            if max_pages and pages_processed >= max_pages:
                break

            payload = self._galsen_get(
                f"{_GALSEN_API_BASE}/villages/",
                {"page": page, "page_size": page_size},
            )
            rows = payload.get("results", []) if isinstance(payload, dict) else []
            if not rows:
                break

            scanned += len(rows)
            candidates = []
            for item in rows:
                village_id = item.get("id")
                village_name = (item.get("nom") or "").strip()
                commune_id = item.get("commune")
                region_pcode = item.get("region")

                if isinstance(commune_id, dict):
                    commune_id = commune_id.get("id")
                try:
                    commune_id = int(commune_id)
                except (TypeError, ValueError):
                    commune_id = False

                if not village_id or not village_name:
                    skipped += 1
                    continue

                parent = communes.get(commune_id) if commune_id else False
                if not parent and region_pcode:
                    parent = Geo.search([
                        ("country_id", "=", self.id),
                        ("niveau", "=", "niveau1"),
                        ("active", "=", True),
                        ("source_uid", "=", f"GALSEN-REGION-{region_pcode}"),
                    ], limit=1)
                if not parent:
                    skipped += 1
                    continue

                candidates.append((
                    f"GALSEN-VILLAGE-{village_id}",
                    village_id,
                    village_name,
                    parent,
                ))

            if candidates:
                uids = [item[0] for item in candidates]
                existing = Geo.search([
                    ("country_id", "=", self.id),
                    ("niveau", "=", "niveau5"),
                    ("source_uid", "in", uids),
                ])
                existing_by_uid = {record.source_uid: record for record in existing}
                create_vals = []

                for source_uid, village_id, village_name, parent in candidates:
                    values = {
                        "name": village_name,
                        "code": str(village_id),
                        "country_id": self.id,
                        "parent_id": parent.id,
                        "niveau": "niveau5",
                        "source_admin_level": "MANUAL",
                        "designation_locale": "Village / quartier / unité locale",
                        "source": "GalsenAPI",
                        "source_url": f"{_GALSEN_API_BASE}/villages/{village_id}/",
                        "active": True,
                    }
                    record = existing_by_uid.get(source_uid)
                    if record:
                        record.write(values)
                        updated += 1
                    else:
                        values["source_uid"] = source_uid
                        create_vals.append(values)

                if create_vals:
                    Geo.create(create_vals)
                    loaded += len(create_vals)

            pages_processed += 1
            page += 1
            self.env.cr.commit()

            if target and loaded >= target:
                break
            if len(rows) < page_size:
                break

        return loaded, updated, max(start_page, page - 1), skipped, scanned

    def _load_senegal_quartiers(
        self, communes, minimum_units=200, start_page=1, max_pages=None
    ):
        """Compatibilité : le chargeur utilise désormais GalsenAPI sans ANSD."""
        return self._load_senegal_villages_galsen(
            communes,
            page_size=200,
            limit=minimum_units if minimum_units else None,
            start_page=start_page,
            max_pages=max_pages,
        )

    def _set_senegal_geography_status(self, message):
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
            "kiiraaye_geo_quartier_label": "Quartier / unité locale",
            "kiiraaye_geo_status": "ok",
            "kiiraaye_geo_last_sync": fields.Datetime.now(),
            "kiiraaye_geo_message": message,
        })

    def action_load_senegal_quartiers(self):
        """Compatibilité : charge tous les villages GalsenAPI."""
        self.ensure_one()
        return self.action_load_senegal_all_villages()

    def action_load_senegal_all_villages(self):
        """Charge tous les villages GalsenAPI en une seule opération."""
        self.ensure_one()
        if self.code != "SN":
            raise UserError(_("Cette opération est réservée au Sénégal."))

        root = self._ensure_senegal_root()
        Geo = self.env["kiiraaye.geographie"].sudo()

        regions = Geo.search([
            ("country_id", "=", self.id),
            ("niveau", "=", "niveau1"),
            ("active", "=", True),
        ])
        if not regions:
            regions = self._load_senegal_regions(root)

        departments = Geo.search([
            ("country_id", "=", self.id),
            ("niveau", "=", "niveau2"),
            ("active", "=", True),
        ])
        if not departments:
            dept_map = {}
            for region in regions:
                dept_map[region.source_uid.replace("GALSEN-REGION-", "")] = region
            departments = self._load_senegal_departments(dept_map).values()

        dept_map = {}
        for dept in departments:
            dept_map[dept.source_uid.replace("GALSEN-DEPT-", "")] = dept
        communes = self._load_senegal_communes(dept_map)
        if not communes:
            raise UserError(_("Impossible de charger les communes du Sénégal depuis GalsenAPI."))

        loaded, updated, last_page, skipped, scanned = self._load_senegal_villages_galsen(
            communes, page_size=200, limit=None, start_page=1, max_pages=None
        )

        final_count = Geo.search_count([
            ("country_id", "=", self.id),
            ("niveau", "=", "niveau5"),
            ("active", "=", True),
            ("source", "=", "GalsenAPI"),
        ])
        message = _(
            "GalsenAPI : import complet terminé. %s villages actifs dans Odoo. "
            "Créés : %s, mis à jour : %s, pages traitées : %s, "
            "lignes analysées : %s, ignorées : %s."
        ) % (final_count, loaded, updated, last_page, scanned, skipped)

        self.sudo().write({
            "kiiraaye_geo_village_page": last_page,
            "kiiraaye_geo_village_loaded": final_count,
        })
        self._set_senegal_geography_status(message)
        self.env.cr.commit()

        return {
            "type": "ir.actions.client",
            "tag": "display_notification",
            "params": {
                "title": _("Villages GalsenAPI"),
                "message": message,
                "type": "success",
                "sticky": False,
            },
        }

    def action_load_senegal_default_geography(self):
        self.ensure_one()
        if self.code != "SN":
            raise UserError(_("Cette opération est réservée au Sénégal."))

        root = self._ensure_senegal_root()
        regions = self._load_senegal_regions(root)
        departments = self._load_senegal_departments(regions)
        self._load_senegal_arrondissements(departments)
        communes = self._load_senegal_communes(departments)
        self.env.cr.commit()

        self._set_senegal_geography_status(
            "Référentiel administratif Sénégal chargé : "
            f"{len(regions)} régions, {len(departments)} départements et "
            f"{len(communes)} communes. "
            "Les villages réels GalsenAPI sont chargés séparément "
            "par lots de 80 avec le bouton dédié."
        )

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
