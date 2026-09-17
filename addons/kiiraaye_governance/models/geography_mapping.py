# -*- coding: utf-8 -*-
import unicodedata

from odoo import models, _


# Libellés administratifs rencontrés couramment dans les sources internationales.
# La correspondance reste configurable sur le pays : ces mots servent uniquement
# à proposer automatiquement le niveau Kiiraaye le plus plausible.
_GEO_CONCEPT_KEYWORDS = {
    "region": (
        "region", "regione", "regioni", "state", "states", "province", "provincia",
        "wilaya", "oblast", "oblasts", "governorate", "gouvernorat", "voivodeship",
        "canton", "departement regional", "territorio regional",
    ),
    "department": (
        "department", "departement", "district", "county", "counties", "prefecture",
        "prefectura", "comarca", "raion", "rayon", "municipal district", "metropolitan district",
    ),
    "commune": (
        "commune", "municipality", "municipalities", "municipio", "municipal", "city",
        "town", "borough", "local government", "urban commune", "rural commune", "council area",
    ),
    "quartier": (
        "quartier", "quarter", "neighborhood", "neighbourhood", "ward", "barangay",
        "sector", "cell", "zone locale", "local zone", "urban ward",
    ),
}


def _normalize(value):
    value = unicodedata.normalize("NFKD", str(value or ""))
    value = "".join(char for char in value if not unicodedata.combining(char))
    return " ".join(value.lower().replace("_", " ").split())


class ResCountryGeographyMapping(models.Model):
    _inherit = "res.country"

    def _find_source_level_by_concept(self, metadata, available_levels, concept, min_level=0):
        keywords = _GEO_CONCEPT_KEYWORDS.get(concept, ())
        candidates = []
        for level in sorted(available_levels):
            if level <= min_level:
                continue
            item = metadata.get(level) or {}
            canonical = _normalize(item.get("boundaryCanonical"))
            if not canonical:
                continue
            score = 0
            for keyword in keywords:
                normalized_keyword = _normalize(keyword)
                if canonical == normalized_keyword:
                    score = 100
                    break
                if normalized_keyword in canonical:
                    score = max(score, 50)
            if score:
                candidates.append((score, level))
        if not candidates:
            return None
        candidates.sort(key=lambda item: (-item[0], item[1]))
        return candidates[0][1]

    def _concept_level_mapping(self, result):
        """Détermine la correspondance conceptuelle à partir des libellés de la source.

        Le niveau normalisé dans kiiraaye.geographie reste lié à l'ADM source
        (ADM1 -> niveau1, ADM2 -> niveau2, ...). En revanche, les champs du pays
        Région/Département/Commune/Quartier sont affectés selon la désignation
        administrative réelle lorsqu'elle est identifiable.
        """
        available = sorted(result.get("layers", []))
        metadata = result.get("metadata", {}) or {}
        if not available:
            return {}

        mapping = {}
        used = set()

        region = self._find_source_level_by_concept(metadata, available, "region", 0)
        if region is None:
            region = available[0]
        mapping["kiiraaye_geo_region_level"] = f"niveau{region}"
        used.add(region)

        department = self._find_source_level_by_concept(metadata, available, "department", region)
        if department is None:
            remaining = [level for level in available if level > region and level not in used]
            department = remaining[0] if remaining else None
        if department:
            mapping["kiiraaye_geo_department_level"] = f"niveau{department}"
            used.add(department)
        else:
            mapping["kiiraaye_geo_department_level"] = ""

        commune_min = department or region
        commune = self._find_source_level_by_concept(metadata, available, "commune", commune_min)
        if commune is None:
            # Un repli ordinal n'est utilisé que si le niveau source possède
            # au moins quatre niveaux : dans ce cas, les sources globales ont
            # généralement une maille locale supplémentaire exploitable.
            remaining = [level for level in available if level > commune_min and level not in used]
            if len(available) >= 4 and remaining:
                commune = remaining[0]
        if commune:
            mapping["kiiraaye_geo_commune_level"] = f"niveau{commune}"
            used.add(commune)
        else:
            mapping["kiiraaye_geo_commune_level"] = ""

        quartier_min = commune or department or region
        quartier = self._find_source_level_by_concept(metadata, available, "quartier", quartier_min)
        if quartier is None:
            remaining = [level for level in available if level > quartier_min and level not in used]
            if len(remaining) == 1:
                quartier = remaining[0]
        if quartier:
            mapping["kiiraaye_geo_quartier_level"] = f"niveau{quartier}"
            used.add(quartier)
        else:
            mapping["kiiraaye_geo_quartier_level"] = ""

        return mapping

    def _country_concept_label(self, metadata, level, base_label):
        if not level:
            return base_label
        try:
            source_level = int(str(level).replace("niveau", ""))
        except (TypeError, ValueError):
            return base_label
        canonical = _normalize((metadata.get(source_level) or {}).get("boundaryCanonical"))
        if not canonical:
            return base_label
        pretty = canonical.replace("_", " ").strip()
        if pretty.lower() in _normalize(base_label):
            return base_label
        return f"{base_label} / {pretty.title()}"

    def _auto_adapt_configuration(self, result):
        self.ensure_one()
        if not self.kiiraaye_geo_auto_adapt:
            return

        metadata = result.get("metadata", {}) or {}
        mapping = self._concept_level_mapping(result)
        vals = dict(mapping)

        labels = (
            ("kiiraaye_geo_region_level", "kiiraaye_geo_region_label", "Région / État / Province"),
            ("kiiraaye_geo_department_level", "kiiraaye_geo_department_label", "Département / District / Comté"),
            ("kiiraaye_geo_commune_level", "kiiraaye_geo_commune_label", "Commune / Municipalité / Ville"),
            ("kiiraaye_geo_quartier_level", "kiiraaye_geo_quartier_label", "Quartier / équivalent local"),
        )
        for level_field, label_field, base_label in labels:
            vals[label_field] = self._country_concept_label(
                metadata,
                vals.get(level_field),
                base_label,
            )

        self.sudo().write(vals)

        details = []
        for level_field, _label_field, base_label in labels:
            value = vals.get(level_field) or "Aucun"
            details.append(f"{base_label} = {value}")
        result["concept_mapping"] = mapping
        result["concept_mapping_details"] = details

    def action_sync_kiiraaye_geography(self):
        """Synchronise les subdivisions du pays puis adapte les concepts métier."""
        # La méthode originale effectue l'import et appelle _auto_adapt_configuration.
        # Cette surcharge conserve le comportement natif tout en fournissant la
        # correspondance sémantique via la méthode ci-dessus.
        return super().action_sync_kiiraaye_geography()
