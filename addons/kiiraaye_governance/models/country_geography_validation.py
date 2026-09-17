from odoo import api, models, _
from odoo.exceptions import ValidationError


class ResCountryGeographyValidation(models.Model):
    _inherit = "res.country"

    @api.constrains(
        "kiiraaye_geo_region_level",
        "kiiraaye_geo_department_level",
        "kiiraaye_geo_commune_level",
        "kiiraaye_geo_quartier_level",
    )
    def _check_kiiraaye_geo_level_mapping(self):
        rank = {
            "niveau1": 1,
            "niveau2": 2,
            "niveau3": 3,
            "niveau4": 4,
            "niveau5": 5,
            "niveau6": 6,
            "localite": 99,
        }
        fields_by_role = (
            ("Région", "kiiraaye_geo_region_level"),
            ("Département", "kiiraaye_geo_department_level"),
            ("Commune", "kiiraaye_geo_commune_level"),
            ("Quartier", "kiiraaye_geo_quartier_level"),
        )
        for country in self:
            seen = {}
            previous_rank = 0
            for label, field_name in fields_by_role:
                level = getattr(country, field_name)
                if not level:
                    continue
                current_rank = rank.get(level, 99)
                if level in seen:
                    raise ValidationError(
                        _(
                            "Le niveau géographique « %s » est utilisé plusieurs fois dans la configuration de %s."
                        )
                        % (level, country.name)
                    )
                if current_rank < previous_rank:
                    raise ValidationError(
                        _(
                            "La configuration géographique de %s doit suivre l'ordre hiérarchique Région → Département → Commune → Quartier."
                        )
                        % country.name
                    )
                seen[level] = label
                previous_rank = current_rank
