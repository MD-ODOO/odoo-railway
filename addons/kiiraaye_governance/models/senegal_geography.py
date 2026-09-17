# -*- coding: utf-8 -*-
import csv
import hashlib
import io
import logging
import re
import unicodedata

from odoo import fields, models, _
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)

_GALSEN_API_BASE = "https://galsenapi.lassanasiby.com/api/v1"
_ANSD_LOCALITES_URL = (
    "https://www.ansd.sn/data-recensement.csv"
    "?field_liste_annee_value=2023&_format=csv"
)
_ANSD_LOCALITES_SOURCE_URL = "https://www.ansd.sn/donnees-recensements"
_ANSD_LOCALITES_SOURCE = "ANSD - RGPH-5 2023, Répertoire des localités"


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

    @staticmethod
    def _ansd_get_csv():
        from urllib.error import HTTPError, URLError
        from urllib.request import Request, urlopen

        try:
            request = Request(
                _ANSD_LOCALITES_URL,
                headers={
                    "User-Agent": "Kiiraaye-Gouvernance/19.0",
                    "Accept": "text/csv,application/csv;q=0.9,*/*;q=0.8",
                },
            )
            with urlopen(request, timeout=180) as response:
                return response.read().decode("utf-8-sig")
        except (HTTPError, URLError, TimeoutError, UnicodeDecodeError) as exc:
            raise UserError(
                _("Impossible de récupérer le Répertoire des localités ANSD depuis %s.\n\n%s")
                % (_ANSD_LOCALITES_URL, exc)
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

    @staticmethod
    def _normalize_local_label(value):
        value = unicodedata.normalize("NFKD", str(value or ""))
        value = value.encode("ascii", "ignore").decode("ascii")
        value = value.lower().strip()
        value = re.sub(r"[^a-z0-9]+", " ", value)
        return re.sub(r"\s+", " ", value).strip()

    @classmethod
    def _locality_uid(cls, department_id, commune_name, locality_name, com_arrt_ville):
        raw = "|".join(
            [
                str(department_id),
                cls._normalize_local_label(commune_name),
                cls._normalize_local_label(locality_name),
                cls._normalize_local_label(com_arrt_ville),
            ]
        )
        digest = hashlib.sha1(raw.encode("utf-8")).hexdigest()[:20]
        return f"ANSD-RGPH5-LOCALITE-{digest}"

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

    def _load_senegal_quartiers(self, communes):
        """Charge les unités locales du répertoire ANSD sous leur commune.

        L'ANSD expose la colonne « QUARTIER/VILLAGE/HAMEAU ». La source ne fournit
        pas dans ce flux un type permettant de distinguer automatiquement quartier,
        village et hameau. Les lignes sont donc conservées fidèlement comme unités
        locales de niveau 5, sans les présenter comme des quartiers administratifs
        officiellement homogènes.
        """
        csv_text = self._ansd_get_csv()
        reader = csv.DictReader(io.StringIO(csv_text))

        departments_by_name = {}
        for department in set(commune.parent_id for commune in communes.values() if commune.parent_id):
            departments_by_name.setdefault(
                self._normalize_local_label(department.name), department
            )

        communes_by_key = {}
        for commune in communes.values():
            department = commune.parent_id
            if not department:
                continue
            communes_by_key[
                (
                    department.id,
                    self._normalize_local_label(commune.name),
                )
            ] = commune

        seen = set()
        loaded = 0
        skipped = 0
        for row in reader:
            region = (row.get("Region") or "").strip()
            department_name = (row.get("Departement") or "").strip()
            commune_name = (row.get("COMMUNE") or "").strip()
            com_arrt_ville = (row.get("COM_ARRT_VILLE") or "").strip()
            locality_name = (
                row.get("QUARTIER/VILLAGE/HAMEAU")
                or row.get("LOCALITE")
                or ""
            ).strip()
            if not department_name or not commune_name or not locality_name:
                skipped += 1
                continue

            department = departments_by_name.get(self._normalize_local_label(department_name))
            if not department:
                skipped += 1
                continue

            commune = communes_by_key.get(
                (department.id, self._normalize_local_label(commune_name))
            )
            if not commune:
                skipped += 1
                continue

            locality_key = (
                commune.id,
                self._normalize_local_label(locality_name),
                self._normalize_local_label(com_arrt_ville),
            )
            if locality_key in seen:
                continue
            seen.add(locality_key)

            source_uid = self._locality_uid(
                department.id,
                commune.name,
                locality_name,
                com_arrt_ville,
            )
            self._upsert_senegal_geo(
                source_uid,
                {
                    "name": locality_name,
                    "code": source_uid[-12:],
                    "country_id": self.id,
                    "parent_id": commune.id,
                    "niveau": "niveau5",
                    "source_admin_level": "MANUAL",
                    "designation_locale": "Quartier / Village / Hameau",
                    "source": _ANSD_LOCALITES_SOURCE,
                    "source_url": _ANSD_LOCALITES_SOURCE_URL,
                    "source_year": 2023,
                    "source_license": "CC BY 4.0",
                    "active": True,
                },
            )
            loaded += 1

        _logger.info(
            "Géographie Sénégal : %s unités locales ANSD chargées en niveau 5, %s lignes ignorées.",
            loaded,
            skipped,
        )
        return loaded, skipped

    def action_load_senegal_default_geography(self):
        self.ensure_one()
        if self.code != "SN":
            raise UserError(_("Cette opération est réservée au Sénégal."))

        root = self._ensure_senegal_root()
        regions = self._load_senegal_regions(root)
        departments = self._load_senegal_departments(regions)
        self._load_senegal_arrondissements(departments)
        communes = self._load_senegal_communes(departments)
        quartiers, skipped_localities = self._load_senegal_quartiers(communes)

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
            "kiiraaye_geo_message": (
                "Référentiel Sénégal chargé automatiquement : "
                f"{len(regions)} régions, {len(departments)} départements, "
                f"{len(communes)} communes, {quartiers} unités locales de niveau 5. "
                "Le niveau 5 reprend fidèlement la colonne ANSD « Quartier/Village/Hameau » "
                f"({skipped_localities} lignes ignorées faute de rattachement exploitable)."
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
