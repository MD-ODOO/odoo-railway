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

    def _load_senegal_quartiers(self, communes):
        """Charge les unités locales réelles sous les communes.

        Priorité au répertoire ANSD RGPH-5 2023. Lorsque le flux ANSD courant
        ne permet pas de rattacher suffisamment d'unités, un repli GalsenAPI
        est utilisé. GalsenAPI expose les villages avec leur commune et
        constitue une source réelle complémentaire pour le référentiel local.
        """
        Geo = self.env["kiiraaye.geographie"].sudo()

        loaded_ansd = 0
        skipped_ansd = 0

        # 1) Source ANSD : répertoire officiel des localités RGPH-5 2023.
        try:
            csv_text = self._ansd_get_csv()

            try:
                dialect = csv.Sniffer().sniff(csv_text[:12000], delimiters=",;\\t|")
            except csv.Error:
                dialect = csv.excel

            reader = csv.DictReader(io.StringIO(csv_text), dialect=dialect)
            if reader.fieldnames:
                normalized_headers = {
                    self._normalize_csv_header(header): header
                    for header in reader.fieldnames
                    if header
                }

                def row_value(row, name):
                    original = normalized_headers.get(name)
                    return (row.get(original) or "").strip() if original else ""

                communes_by_key = {}
                for commune in communes.values():
                    department = commune.parent_id
                    if not department:
                        continue
                    communes_by_key[
                        (
                            self._normalize_match_label(department.name),
                            self._normalize_match_label(commune.name),
                        )
                    ] = commune

                communes_by_code = {
                    self._normalize_match_label(commune.code): commune
                    for commune in communes.values()
                    if commune.code
                }

                seen = set()
                for row in reader:
                    department_name = row_value(row, "departement")
                    commune_name = row_value(row, "commune")
                    com_arrt_ville = row_value(row, "com_arrt_ville")
                    locality_name = (
                        row_value(row, "quartier_village_hameau")
                        or row_value(row, "localite")
                    )

                    if not department_name or not commune_name or not locality_name:
                        skipped_ansd += 1
                        continue

                    commune = communes_by_key.get(
                        (
                            self._normalize_match_label(department_name),
                            self._normalize_match_label(commune_name),
                        )
                    )

                    if not commune:
                        commune_code = (
                            row_value(row, "code_commune")
                            or row_value(row, "id_commune")
                        )
                        commune = (
                            communes_by_code.get(
                                self._normalize_match_label(commune_code)
                            )
                            if commune_code
                            else False
                        )

                    if not commune:
                        skipped_ansd += 1
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
                        commune.parent_id.id,
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
                    loaded_ansd += 1
        except UserError as exc:
            _logger.warning(
                "Géographie Sénégal : chargement ANSD indisponible, "
                "fallback GalsenAPI activé : %s",
                exc,
            )

        # 2) Fallback réel GalsenAPI si l'import ANSD actuel est trop pauvre.
        # Trois unités ou quelques lignes seulement indiquent généralement
        # un changement de structure du flux ANSD ; on complète alors avec
        # les villages GalsenAPI, qui sont directement rattachés à leur commune.
        loaded_galsen = 0
        if loaded_ansd < 100:
            try:
                villages = self._galsen_get_all("villages")
                seen_uids = {
                    value
                    for value in Geo.search(
                        [
                            ("country_id", "=", self.id),
                            ("niveau", "=", "niveau5"),
                            ("active", "=", True),
                            ("source_uid", "like", "GALSEN-VILLAGE-%"),
                        ]
                    ).mapped("source_uid")
                    if value
                }

                for item in villages:
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
                            "designation_locale": "Village / unité locale",
                            "source": "GalsenAPI (Galsenify, données publiques)",
                            "source_url": f"{_GALSEN_API_BASE}/villages/{village_id}/",
                            "active": True,
                        },
                    )
                    seen_uids.add(source_uid)
                    loaded_galsen += 1
            except UserError as exc:
                _logger.warning(
                    "Géographie Sénégal : fallback GalsenAPI indisponible : %s",
                    exc,
                )

        total_loaded = loaded_ansd + loaded_galsen
        _logger.info(
            "Géographie Sénégal : %s unités locales chargées "
            "(ANSD=%s, GalsenAPI=%s), %s lignes ANSD ignorées.",
            total_loaded,
            loaded_ansd,
            loaded_galsen,
            skipped_ansd,
        )
        return total_loaded, skipped_ansd


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
        """Charge uniquement les quartiers/unités locales sous les communes existantes."""
        self.ensure_one()
        if self.code != "SN":
            raise UserError(_("Cette opération est réservée au Sénégal."))

        Geo = self.env["kiiraaye.geographie"].sudo()
        commune_records = Geo.search([
            ("country_id", "=", self.id),
            ("niveau", "=", "niveau3"),
            ("active", "=", True),
        ])

        # Si les communes n'existent pas encore, on construit d'abord le
        # référentiel administratif. Le chargement des unités locales reste
        # ensuite ciblé sur les communes.
        if not commune_records:
            self.action_load_senegal_default_geography()
            commune_records = Geo.search([
                ("country_id", "=", self.id),
                ("niveau", "=", "niveau3"),
                ("active", "=", True),
            ])

        communes = {record.id: record for record in commune_records}
        loaded, skipped = self._load_senegal_quartiers(communes)
        self._set_senegal_geography_status(
            _(
                "Chargement ANSD terminé : %s unités locales/quartiers rattachées aux %s communes. "
                "%s lignes ignorées faute de rattachement exploitable."
            ) % (loaded, len(communes), skipped)
        )

        return {
            "type": "ir.actions.client",
            "tag": "display_notification",
            "params": {
                "title": _("Quartiers / unités locales chargés"),
                "message": self.kiiraaye_geo_message,
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
        quartiers, skipped_localities = self._load_senegal_quartiers(communes)

        self._set_senegal_geography_status(
            "Référentiel Sénégal chargé automatiquement : "
            f"{len(regions)} régions, {len(departments)} départements, "
            f"{len(communes)} communes, {quartiers} unités locales de niveau 5. "
            "Le niveau 5 reprend fidèlement la colonne ANSD « Quartier/Village/Hameau » "
            f"({skipped_localities} lignes ignorées faute de rattachement exploitable)."
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
