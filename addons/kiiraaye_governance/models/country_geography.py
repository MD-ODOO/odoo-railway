# -*- coding: utf-8 -*-
import json
import math
import re
from datetime import datetime
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from odoo import api, fields, models, _
from odoo.exceptions import UserError


_GEOBOUNDARIES_API = "https://www.geoboundaries.org/api/current/gbOpen/{iso3}/ADM{level}/"
_RESTCOUNTRIES_API = "https://restcountries.com/v3.1/alpha/{iso2}"

_SOURCE_TO_LEVEL = {
    1: "niveau1",
    2: "niveau2",
    3: "niveau3",
    4: "niveau4",
    5: "niveau5",
}

_GEO_LEVEL_SELECTION = [
    ("", "Aucun"),
    ("niveau1", "Niveau 1"),
    ("niveau2", "Niveau 2"),
    ("niveau3", "Niveau 3"),
    ("niveau4", "Niveau 4"),
    ("niveau5", "Niveau 5"),
    ("niveau6", "Niveau 6"),
    ("localite", "Localité / Autre"),
]


class ResCountryGeography(models.Model):
    _inherit = "res.country"

    # ------------------------------------------------------------------
    # Configuration du référentiel par pays
    # ------------------------------------------------------------------
    kiiraaye_iso3 = fields.Char(
        string="Code ISO3",
        size=3,
        index=True,
        help="Code ISO 3166-1 alpha-3 utilisé pour interroger le référentiel administratif.",
    )
    kiiraaye_geo_source = fields.Selection(
        [
            ("geoboundaries", "GeoBoundaries / gbOpen"),
            ("manuel", "Référentiel manuel"),
        ],
        string="Source géographique",
        default="geoboundaries",
        required=True,
        ondelete={
            "geoboundaries": "set default",
            "manuel": "set default",
        },
    )
    kiiraaye_geo_auto_adapt = fields.Boolean(
        string="Adaptation automatique des niveaux",
        default=True,
        help="Affecte automatiquement les niveaux disponibles aux concepts Région, Département, Commune et Quartier.",
    )

    kiiraaye_geo_region_level = fields.Selection(
        _GEO_LEVEL_SELECTION,
        string="Niveau Région / État / Province",
        default="niveau1",
    )
    kiiraaye_geo_department_level = fields.Selection(
        _GEO_LEVEL_SELECTION,
        string="Niveau Département / District / Comté",
        default="niveau2",
    )
    kiiraaye_geo_commune_level = fields.Selection(
        _GEO_LEVEL_SELECTION,
        string="Niveau Commune / Municipalité / Ville",
        default="niveau3",
    )
    kiiraaye_geo_quartier_level = fields.Selection(
        _GEO_LEVEL_SELECTION,
        string="Niveau Quartier / équivalent local",
        default="niveau5",
    )

    kiiraaye_geo_region_label = fields.Char(
        string="Libellé local Région",
        default="Région / État / Province",
    )
    kiiraaye_geo_department_label = fields.Char(
        string="Libellé local Département",
        default="Département / District / Comté",
    )
    kiiraaye_geo_commune_label = fields.Char(
        string="Libellé local Commune",
        default="Commune / Municipalité / Ville",
    )
    kiiraaye_geo_quartier_label = fields.Char(
        string="Libellé local Quartier",
        default="Quartier / équivalent local",
    )

    kiiraaye_geo_status = fields.Selection(
        [
            ("never", "Jamais synchronisé"),
            ("ok", "Synchronisé"),
            ("error", "Erreur"),
        ],
        string="État du référentiel",
        default="never",
        readonly=True,
    )
    kiiraaye_geo_last_sync = fields.Datetime(
        string="Dernière synchronisation",
        readonly=True,
    )
    kiiraaye_geo_message = fields.Text(
        string="Informations / résultat de synchronisation",
        readonly=True,
    )

    # ------------------------------------------------------------------
    # Utilitaires réseau / géométrie
    # ------------------------------------------------------------------
    @staticmethod
    def _http_json(url, timeout=60):
        try:
            request = Request(
                url,
                headers={
                    "User-Agent": "Kiiraaye-Gouvernance/19.0",
                    "Accept": "application/json",
                },
            )
            with urlopen(request, timeout=timeout) as response:
                return json.loads(response.read().decode("utf-8"))
        except (HTTPError, URLError, TimeoutError, ValueError) as exc:
            raise UserError(
                _("Impossible de récupérer les données géographiques depuis %s.\n\n%s")
                % (url, exc)
            )

    @staticmethod
    def _extract_year(value):
        match = re.search(r"\d{4}", str(value or ""))
        return int(match.group(0)) if match else False

    @staticmethod
    def _feature_name(properties, fallback):
        for key in ("shapeName", "shapeNameASCII", "name", "NAME", "NAME_0", "NAME_1", "NAME_2"):
            value = properties.get(key)
            if value:
                return str(value).strip()
        return fallback

    @staticmethod
    def _geometry_points(geometry):
        points = []

        def walk(value):
            if isinstance(value, list):
                if len(value) >= 2 and isinstance(value[0], (int, float)) and isinstance(value[1], (int, float)):
                    points.append((float(value[0]), float(value[1])))
                else:
                    for child in value:
                        walk(child)

        walk((geometry or {}).get("coordinates", []))
        return points

    @classmethod
    def _geometry_bbox(cls, geometry):
        points = cls._geometry_points(geometry)
        if not points:
            return None
        xs = [point[0] for point in points]
        ys = [point[1] for point in points]
        return min(xs), min(ys), max(xs), max(ys)

    @staticmethod
    def _polygon_centroid(ring):
        if not ring:
            return None, 0.0
        cleaned = [(float(point[0]), float(point[1])) for point in ring if len(point) >= 2]
        if len(cleaned) < 3:
            x = sum(point[0] for point in cleaned) / len(cleaned)
            y = sum(point[1] for point in cleaned) / len(cleaned)
            return (x, y), 0.0
        if cleaned[0] != cleaned[-1]:
            cleaned.append(cleaned[0])

        area2 = 0.0
        cx = 0.0
        cy = 0.0
        for current, nxt in zip(cleaned, cleaned[1:]):
            cross = current[0] * nxt[1] - nxt[0] * current[1]
            area2 += cross
            cx += (current[0] + nxt[0]) * cross
            cy += (current[1] + nxt[1]) * cross

        if abs(area2) < 1e-12:
            x = sum(point[0] for point in cleaned[:-1]) / max(len(cleaned) - 1, 1)
            y = sum(point[1] for point in cleaned[:-1]) / max(len(cleaned) - 1, 1)
            return (x, y), 0.0

        area = area2 / 2.0
        return (cx / (3.0 * area2), cy / (3.0 * area2)), abs(area)

    @classmethod
    def _geometry_representative_point(cls, geometry):
        geometry = geometry or {}
        geometry_type = geometry.get("type")
        coordinates = geometry.get("coordinates", [])

        if geometry_type == "Polygon":
            point, _area = cls._polygon_centroid(coordinates[0] if coordinates else [])
            if point:
                return point

        if geometry_type == "MultiPolygon":
            best = None
            best_area = -1.0
            for polygon in coordinates:
                point, area = cls._polygon_centroid(polygon[0] if polygon else [])
                if point and area > best_area:
                    best = point
                    best_area = area
            if best:
                return best

        bbox = cls._geometry_bbox(geometry)
        if bbox:
            xmin, ymin, xmax, ymax = bbox
            return ((xmin + xmax) / 2.0, (ymin + ymax) / 2.0)

        points = cls._geometry_points(geometry)
        return points[0] if points else None

    @staticmethod
    def _point_in_ring(point, ring):
        x, y = point
        inside = False
        if not ring:
            return False
        points = [(float(p[0]), float(p[1])) for p in ring if len(p) >= 2]
        if len(points) < 3:
            return False
        if points[0] != points[-1]:
            points.append(points[0])

        for index in range(len(points) - 1):
            x1, y1 = points[index]
            x2, y2 = points[index + 1]
            intersects = ((y1 > y) != (y2 > y)) and (
                x < (x2 - x1) * (y - y1) / ((y2 - y1) or 1e-20) + x1
            )
            if intersects:
                inside = not inside
        return inside

    @classmethod
    def _point_in_geometry(cls, point, geometry):
        geometry = geometry or {}
        geometry_type = geometry.get("type")
        coordinates = geometry.get("coordinates", [])

        if geometry_type == "Polygon":
            if not coordinates or not cls._point_in_ring(point, coordinates[0]):
                return False
            return not any(cls._point_in_ring(point, hole) for hole in coordinates[1:])

        if geometry_type == "MultiPolygon":
            return any(cls._point_in_geometry(point, {"type": "Polygon", "coordinates": polygon}) for polygon in coordinates)

        return False

    @classmethod
    def _find_parent(cls, geometry, parent_items):
        point = cls._geometry_representative_point(geometry)
        if not point:
            return None

        px, py = point
        candidates = []
        for item in parent_items:
            bbox = item["bbox"]
            if bbox:
                xmin, ymin, xmax, ymax = bbox
                if xmin - 1e-9 <= px <= xmax + 1e-9 and ymin - 1e-9 <= py <= ymax + 1e-9:
                    candidates.append(item)
            else:
                candidates.append(item)

        for item in candidates:
            if cls._point_in_geometry(point, item["geometry"]):
                return item["record"]

        bbox = cls._geometry_bbox(geometry)
        if bbox:
            center = ((bbox[0] + bbox[2]) / 2.0, (bbox[1] + bbox[3]) / 2.0)
            for item in candidates:
                if cls._point_in_geometry(center, item["geometry"]):
                    return item["record"]

        return None

    @staticmethod
    def _canonical_label(base, canonical):
        canonical = (canonical or "").strip()
        if not canonical:
            return base
        translated = canonical.replace("_", " ").strip()
        if translated.lower() in base.lower():
            return base
        return f"{base} / {translated.title()}"

    def _resolve_iso3(self):
        self.ensure_one()
        if self.kiiraaye_iso3 and len(self.kiiraaye_iso3.strip()) == 3:
            return self.kiiraaye_iso3.strip().upper()

        if not self.code:
            raise UserError(_("Le pays %s ne possède pas de code ISO2 exploitable.") % self.display_name)

        payload = self._http_json(_RESTCOUNTRIES_API.format(iso2=self.code.upper()), timeout=30)
        item = payload[0] if isinstance(payload, list) and payload else payload
        iso3 = (item or {}).get("cca3")
        if not iso3:
            raise UserError(
                _("Impossible de déterminer le code ISO3 du pays %s. Renseignez-le manuellement dans la configuration.")
                % self.display_name
            )
        self.sudo().write({"kiiraaye_iso3": iso3.upper()})
        return iso3.upper()

    def _get_geo_metadata(self, iso3, source_level):
        url = _GEOBOUNDARIES_API.format(iso3=iso3, level=source_level)
        try:
            return self._http_json(url)
        except UserError:
            return None

    def _download_features(self, metadata):
        if not metadata:
            return []
        url = metadata.get("simplifiedGeometryGeoJSON") or metadata.get("gjDownloadURL")
        if not url:
            return []
        payload = self._http_json(url, timeout=120)
        if payload.get("type") == "FeatureCollection":
            return payload.get("features", [])
        if payload.get("type") == "Feature":
            return [payload]
        return []

    def _import_country_layers(self, iso3):
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
                    "source": "Odoo / res.country",
                    "source_admin_level": "ADM0",
                    "source_uid": f"COUNTRY-{self.id}",
                }
            )

        layers = []
        unavailable = []
        for source_level in range(1, 6):
            metadata = self._get_geo_metadata(iso3, source_level)
            if not metadata:
                unavailable.append(source_level)
                continue
            features = self._download_features(metadata)
            if not features:
                unavailable.append(source_level)
                continue
            layers.append((source_level, metadata, features))

        if not layers:
            raise UserError(
                _("Aucune subdivision administrative ADM1-ADM5 exploitable n'a été trouvée pour %s (%s).")
                % (self.name, iso3)
            )

        imported_uids = set()
        records_by_source_level = {}
        source_meta_by_level = {}

        for source_level, metadata, features in layers:
            normalized_level = _SOURCE_TO_LEVEL[source_level]
            source_meta_by_level[source_level] = metadata
            parent_source_levels = [level for level in records_by_source_level if level < source_level]
            parent_level = max(parent_source_levels) if parent_source_levels else None
            parent_items = records_by_source_level.get(parent_level, []) if parent_level else []

            current_items = []
            for index, feature in enumerate(features, start=1):
                properties = feature.get("properties") or {}
                geometry = feature.get("geometry") or {}
                source_uid = str(
                    properties.get("shapeID")
                    or properties.get("shapeId")
                    or feature.get("id")
                    or f"{iso3}-ADM{source_level}-{index}"
                )
                name = self._feature_name(properties, f"ADM{source_level} #{index}")
                parent = Geo.search(
                    [("id", "=", root.id)],
                    limit=1,
                )
                if parent_items:
                    parent = self._find_parent(geometry, parent_items)
                    if not parent:
                        raise UserError(
                            _(
                                "Impossible de rattacher l'unité « %s » (ADM%s) à son niveau administratif parent."
                            )
                            % (name, source_level)
                        )

                values = {
                    "name": name,
                    "code": properties.get("shapeISO") or source_uid,
                    "country_id": self.id,
                    "parent_id": parent.id if parent else root.id,
                    "niveau": normalized_level,
                    "source_admin_level": f"ADM{source_level}",
                    "designation_locale": metadata.get("boundaryCanonical") or "",
                    "source": "GeoBoundaries / gbOpen",
                    "source_uid": source_uid,
                    "source_url": metadata.get("simplifiedGeometryGeoJSON") or metadata.get("gjDownloadURL") or "",
                    "source_year": self._extract_year(metadata.get("boundaryYearRepresented")),
                    "source_license": metadata.get("boundaryLicense") or "CC-BY 4.0",
                    "active": True,
                }

                record = Geo.search(
                    [("country_id", "=", self.id), ("source_uid", "=", source_uid)],
                    limit=1,
                )
                if record:
                    record.write(values)
                else:
                    record = Geo.create(values)

                imported_uids.add(source_uid)
                current_items.append(
                    {
                        "record": record,
                        "geometry": geometry,
                        "bbox": self._geometry_bbox(geometry),
                    }
                )

            records_by_source_level[source_level] = current_items

        stale = Geo.search([
            ("country_id", "=", self.id),
            ("source", "=", "GeoBoundaries / gbOpen"),
            ("niveau", "!=", "pays"),
            ("source_uid", "not in", list(imported_uids) or [""]),
        ])
        if stale:
            stale.write({"active": False})

        return {
            "layers": [level for level, _meta, _features in layers],
            "unavailable": unavailable,
            "counts": {
                _SOURCE_TO_LEVEL[level]: sum(len(items) for imported_level, items in records_by_source_level.items() if imported_level == level)
                for level in records_by_source_level
            },
            "metadata": source_meta_by_level,
        }

    def _auto_adapt_configuration(self, result):
        if not self.kiiraaye_geo_auto_adapt:
            return

        available = sorted(result.get("layers", []))
        mapped = [_SOURCE_TO_LEVEL[level] for level in available]

        vals = {
            "kiiraaye_geo_region_level": mapped[0] if len(mapped) >= 1 else "",
            "kiiraaye_geo_department_level": mapped[1] if len(mapped) >= 2 else "",
            "kiiraaye_geo_commune_level": mapped[2] if len(mapped) >= 3 else "",
            "kiiraaye_geo_quartier_level": mapped[-1] if len(mapped) >= 4 else "",
        }

        base_labels = {
            "kiiraaye_geo_region_label": "Région / État / Province",
            "kiiraaye_geo_department_label": "Département / District / Comté",
            "kiiraaye_geo_commune_label": "Commune / Municipalité / Ville",
            "kiiraaye_geo_quartier_label": "Quartier / équivalent local",
        }

        concepts = [
            ("kiiraaye_geo_region_level", "kiiraaye_geo_region_label", "Région / État / Province"),
            ("kiiraaye_geo_department_level", "kiiraaye_geo_department_label", "Département / District / Comté"),
            ("kiiraaye_geo_commune_level", "kiiraaye_geo_commune_label", "Commune / Municipalité / Ville"),
            ("kiiraaye_geo_quartier_level", "kiiraaye_geo_quartier_label", "Quartier / équivalent local"),
        ]

        for level_field, label_field, base in concepts:
            source_level = None
            selected = vals.get(level_field)
            for number, normalized in _SOURCE_TO_LEVEL.items():
                if normalized == selected:
                    source_level = number
                    break
            canonical = ""
            if source_level:
                canonical = (result.get("metadata", {}).get(source_level) or {}).get("boundaryCanonical") or ""
            vals[label_field] = self._canonical_label(base, canonical) if selected else base

        self.sudo().write(vals)

    def action_sync_kiiraaye_geography(self):
        """Synchronise les subdivisions disponibles pour ce pays via GeoBoundaries."""
        self.ensure_one()
        if self.kiiraaye_geo_source != "geoboundaries":
            raise UserError(
                _("La source actuelle de %s est configurée sur « Référentiel manuel ». Sélectionnez GeoBoundaries pour lancer une synchronisation automatique.")
                % self.display_name
            )

        try:
            iso3 = self._resolve_iso3()
            result = self._import_country_layers(iso3)
            self._auto_adapt_configuration(result)

            counts = result.get("counts", {})
            summary = _(
                "Synchronisation terminée pour %s (%s).\n"
                "Niveaux chargés : %s.\n"
                "Unités importées : %s."
            ) % (
                self.display_name,
                iso3,
                ", ".join(f"ADM{k}" for k in result.get("layers", [])),
                ", ".join(f"{level}: {count}" for level, count in counts.items()),
            )
            if result.get("unavailable"):
                summary += _("\nNiveaux non disponibles : %s.") % ", ".join(
                    f"ADM{k}" for k in result["unavailable"]
                )

            self.sudo().write({
                "kiiraaye_geo_status": "ok",
                "kiiraaye_geo_last_sync": fields.Datetime.now(),
                "kiiraaye_geo_message": summary,
            })
            return {
                "type": "ir.actions.client",
                "tag": "display_notification",
                "params": {
                    "title": _("Géographie synchronisée"),
                    "message": summary,
                    "type": "success",
                    "sticky": False,
                },
            }
        except UserError as exc:
            self.sudo().write({
                "kiiraaye_geo_status": "error",
                "kiiraaye_geo_last_sync": fields.Datetime.now(),
                "kiiraaye_geo_message": str(exc),
            })
            raise
        except Exception as exc:
            self.sudo().write({
                "kiiraaye_geo_status": "error",
                "kiiraaye_geo_last_sync": fields.Datetime.now(),
                "kiiraaye_geo_message": str(exc),
            })
            raise UserError(
                _("La synchronisation géographique a échoué pour %s.\n\n%s")
                % (self.display_name, exc)
            )
