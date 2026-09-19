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

    kiiraaye_geo_village_page = fields.Integer(
        string="Page villages GalsenAPI",
        default=0,
        readonly=True,
        copy=False,
        help="Dernière page de villages GalsenAPI traitée avec succès.",
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

    @staticmethod
    def _normalize_match_label(value):
        """Clé de rapprochement tolérante aux accents, espaces et ponctuation."""
        value = unicodedata.normalize("NFKD", str(value or ""))
        value = value.encode("ascii", "ignore").decode("ascii")
        return re.sub(r"[^a-z0-9]+", "", value.lower())

    @classmethod
    def _normalize_csv_header(cls, value):
        value = unicodedata.normalize("NFKD", str(value or ""))
        value = value.encode("ascii", "ignore").decode("ascii")
        value = value.lower().strip()
        value = re.sub(r"[^a-z0-9]+", "_", value)
        return re.sub(r"_+", "_", value).strip("_")

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

    def _load_senegal_villages_galsen(
        self, communes, page_size=80, limit=None, start_page=1, max_pages=None
    ):
        """Charge les villages réels de GalsenAPI par pages de 80.

        ``communes`` doit être indexé avec l'identifiant GalsenAPI de la
        commune. ``limit`` limite le nombre de nouveaux villages créés et
        ``max_pages`` limite le nombre de pages API parcourues.
        """
        Geo = self.env["kiiraaye.geographie"].sudo()
        seen_uids = set(
            Geo.search([
                ("country_id", "=", self.id),
                ("niveau", "=", "niveau5"),
                ("source_uid", "like", "GALSEN-VILLAGE-%"),
            ]).mapped("source_uid")
        )

        loaded = 0
        page = max(1, int(start_page or 1))
        target = int(limit) if limit else None
        processed_pages = 0

        while True:
            if max_pages and processed_pages >= max_pages:
                break

            payload = self._galsen_get(
                f"{_GALSEN_API_BASE}/villages/",
                {"page": page, "page_size": page_size},
            )
            rows = payload.get("results", []) if isinstance(payload, dict) else []
            if not rows:
                break

            for item in rows:
                village_id = item.get("id")
                village_name = (item.get("nom") or "").strip()
                commune_id = item.get("commune")
                if not village_id or not village_name or not commune_id:
                    continue

                commune = communes.get(commune_id)
                if not commune:
                    continue

                source_uid = f"GALSEN-VILLAGE-{village_id}"
                if source_uid in seen_uids:
                    continue

                self._upsert_senegal_geo(
                    source_uid,
                    {
                        "name": village_name,
                        "code": str(village_id),
                        "country_id": self.id,
                        "parent_id": commune.id,
                        "niveau": "niveau5",
                        "source_admin_level": "MANUAL",
                        "designation_locale": "Village / quartier / unité locale",
                        "source": "GalsenAPI (Galsenify, données publiques)",
                        "source_url": f"{_GALSEN_API_BASE}/villages/{village_id}/",
                        "active": True,
                    },
                )
                seen_uids.add(source_uid)
                loaded += 1

                if target and loaded >= target:
                    return loaded, page

            processed_pages += 1
            page += 1

            if len(rows) < page_size:
                break

        return loaded, page - 1

    def _load_senegal_quartiers_ansd(
        self, commune_records, limit=80, start_page=1
    ):
        """Charge les localités réelles ANSD 2023, 80 nouvelles lignes par lot."""
        Geo = self.env["kiiraaye.geographie"].sudo()

        commune_index = {}
        for commune in commune_records:
            department = commune.parent_id
            while department and department.niveau != "niveau2":
                department = department.parent_id
            if not department:
                continue
            region = department.parent_id
            while region and region.niveau != "niveau1":
                region = region.parent_id
            if not region:
                continue

            key = (
                self._normalize_match_label(region.name),
                self._normalize_match_label(department.name),
                self._normalize_match_label(commune.name),
            )
            commune_index[key] = commune

        if not commune_index:
            raise UserError(
                _("Aucune commune exploitable n'est disponible pour rattacher les localités ANSD.")
            )

        existing = Geo.search([
            ("country_id", "=", self.id),
            ("niveau", "=", "niveau5"),
            ("active", "=", True),
        ])
        existing_by_parent_name = {
            (record.parent_id.id, self._normalize_match_label(record.name))
            for record in existing
            if record.parent_id
        }

        imported_uids = set(
            Geo.search([
                ("country_id", "=", self.id),
                ("niveau", "=", "niveau5"),
                ("source_uid", "like", "ANSD-RGPH5-LOCALITE-%"),
            ]).mapped("source_uid")
        )

        csv_text = self._ansd_get_csv()
        if not csv_text.strip():
            raise UserError(_("Le répertoire ANSD des localités est vide."))

        sample = csv_text[:8192]
        try:
            delimiter = csv.Sniffer().sniff(sample, delimiters=",;\\t|").delimiter
        except csv.Error:
            delimiter = ";"

        reader = csv.DictReader(io.StringIO(csv_text), delimiter=delimiter)
        normalized_headers = {
            self._normalize_csv_header(header): header
            for header in (reader.fieldnames or [])
            if header
        }

        if not normalized_headers:
            raise UserError(_("Le fichier CSV ANSD ne contient pas d'en-têtes exploitables."))

        def get_value(row, *candidates):
            for candidate in candidates:
                actual = normalized_headers.get(self._normalize_csv_header(candidate))
                if actual:
                    value = row.get(actual)
                    if value not in (None, ""):
                        return str(value).strip()
            return ""

        created = 0
        skipped = 0
        scanned = 0

        for row in reader:
            scanned += 1
            region_name = get_value(row, "Région", "Region")
            department_name = get_value(row, "Département", "Departement")
            commune_name = get_value(
                row, "COMMUNE", "Commune", "Commune / Municipalité"
            )
            locality_name = get_value(
                row,
                "QUARTIER/VILLAGE/HAMEAU",
                "Quartier/Village/Hameau",
                "Quartier / Village / Hameau",
                "Quartier",
                "Village",
                "Hameau",
            )
            com_arrt_ville = get_value(
                row, "COM ARRT/VILLE", "COM_ARRT/VILLE", "Com Arrt/Ville"
            )

            if not region_name or not department_name or not commune_name or not locality_name:
                skipped += 1
                continue

            key = (
                self._normalize_match_label(region_name),
                self._normalize_match_label(department_name),
                self._normalize_match_label(commune_name),
            )
            commune = commune_index.get(key)
            if not commune:
                skipped += 1
                continue

            source_uid = self._locality_uid(
                department_name,
                commune_name,
                locality_name,
                com_arrt_ville,
            )

            normalized_name = self._normalize_match_label(locality_name)
            if source_uid in imported_uids or (
                commune.id,
                normalized_name,
            ) in existing_by_parent_name:
                continue

            self._upsert_senegal_geo(
                source_uid,
                {
                    "name": locality_name,
                    "code": source_uid.split("-")[-1],
                    "country_id": self.id,
                    "parent_id": commune.id,
                    "niveau": "niveau5",
                    "source_admin_level": "MANUAL",
                    "designation_locale": "Quartier / Village / Hameau",
                    "source": _ANSD_LOCALITES_SOURCE,
                    "source_url": _ANSD_LOCALITES_SOURCE_URL,
                    "active": True,
                },
            )
            imported_uids.add(source_uid)
            existing_by_parent_name.add((commune.id, normalized_name))
            created += 1

            if created >= int(limit or 80):
                break

        return created, max(1, int(start_page or 1)), skipped, scanned

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
        """Charge 80 nouvelles localités réelles du répertoire ANSD 2023."""
        self.ensure_one()
        if self.code != "SN":
            raise UserError(_("Cette opération est réservée au Sénégal."))

        Geo = self.env["kiiraaye.geographie"].sudo()
        commune_records = Geo.search([
            ("country_id", "=", self.id),
            ("niveau", "=", "niveau3"),
            ("active", "=", True),
        ], order="name, id")

        if not commune_records:
            raise UserError(
                _("Les communes du Sénégal doivent être chargées avant les villages/quartiers.")
            )

        try:
            loaded, processed_page, skipped, scanned = self._load_senegal_quartiers_ansd(
                commune_records,
                limit=80,
                start_page=self.kiiraaye_geo_village_page + 1,
            )
        except UserError as exc:
            self.sudo().write({
                "kiiraaye_geo_status": "error",
                "kiiraaye_geo_last_sync": fields.Datetime.now(),
                "kiiraaye_geo_message": str(exc),
            })
            raise

        new_total = self.kiiraaye_geo_village_loaded + loaded
        self.sudo().write({
            "kiiraaye_geo_village_page": processed_page if loaded else self.kiiraaye_geo_village_page,
            "kiiraaye_geo_village_loaded": new_total,
        })

        if loaded:
            message = _(
                "Lot %s : %s nouvelles localités ANSD chargées. "
                "Total chargé : %s. %s lignes analysées, %s non rattachées/ignorées. "
                "Relancez le bouton pour charger les 80 suivantes."
            ) % (
                processed_page,
                loaded,
                new_total,
                scanned,
                skipped,
            )
            notification_type = "success"
        else:
            message = _(
                "Aucune nouvelle localité n'a été chargée. "
                "Le répertoire ANSD a été parcouru pour les communes disponibles. "
                "Total chargé : %s."
            ) % new_total
            notification_type = "warning"

        self._set_senegal_geography_status(message)
        self.env.cr.commit()

        return {
            "type": "ir.actions.client",
            "tag": "display_notification",
            "params": {
                "title": _("Localités ANSD"),
                "message": message,
                "type": notification_type,
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
            "Les quartiers/villages/hameaux ANSD 2023 sont chargés séparément "
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
