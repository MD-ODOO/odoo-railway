# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
from odoo.exceptions import ValidationError


class KiiraayeSectionGeographyConfig(models.Model):
    _inherit = "kiiraaye.section"

    geo_region_level = fields.Selection(
        related="country_id.kiiraaye_geo_region_level",
        string="Niveau Région",
        readonly=True,
    )
    geo_department_level = fields.Selection(
        related="country_id.kiiraaye_geo_department_level",
        string="Niveau Département",
        readonly=True,
    )
    geo_commune_level = fields.Selection(
        related="country_id.kiiraaye_geo_commune_level",
        string="Niveau Commune",
        readonly=True,
    )
    geo_quartier_level = fields.Selection(
        related="country_id.kiiraaye_geo_quartier_level",
        string="Niveau Quartier",
        readonly=True,
    )
    geo_region_label = fields.Char(
        related="country_id.kiiraaye_geo_region_label",
        string="Libellé Région",
        readonly=True,
    )
    geo_department_label = fields.Char(
        related="country_id.kiiraaye_geo_department_label",
        string="Libellé Département",
        readonly=True,
    )
    geo_commune_label = fields.Char(
        related="country_id.kiiraaye_geo_commune_label",
        string="Libellé Commune",
        readonly=True,
    )
    geo_quartier_label = fields.Char(
        related="country_id.kiiraaye_geo_quartier_label",
        string="Libellé Quartier",
        readonly=True,
    )

    def _country_level(self, role):
        self.ensure_one()
        level = getattr(self.country_id, f"kiiraaye_geo_{role}_level", False) or False
        if level:
            return level

        # Le Sénégal utilise la convention Kiiraaye standard lorsque la
        # configuration historique du pays n'a pas encore été migrée.
        if self.country_id.code == "SN":
            return {
                "region": "niveau1",
                "department": "niveau2",
                "commune": "niveau3",
                "quartier": "niveau5",
            }.get(role, False)
        return False

    def _geo_parent(self, role):
        self.ensure_one()
        if role == "region":
            return False
        if role == "department":
            return self.region_id if self._country_level("region") else False
        if role == "commune":
            if self._country_level("department"):
                return self.departement_id
            if self._country_level("region"):
                return self.region_id
            return False
        if role == "quartier":
            if self._country_level("commune"):
                return self.commune_id
            if self._country_level("department"):
                return self.departement_id
            if self._country_level("region"):
                return self.region_id
        return False

    def _geo_domain(self, role):
        self.ensure_one()
        level = self._country_level(role)
        if not self.country_id or not level:
            return [("id", "=", False)]

        domain = [
            ("country_id", "=", self.country_id.id),
            ("niveau", "=", level),
            ("active", "=", True),
        ]
        parent = self._geo_parent(role)
        if parent:
            domain.append(("id", "child_of", parent.id))
        return domain

    def _clear_incompatible_geography(self):
        self.ensure_one()
        if not self.country_id:
            self.region_id = False
            self.departement_id = False
            self.commune_id = False
            self.quartier_id = False
            return

        if not self._country_level("region"):
            self.region_id = False
        if not self._country_level("department"):
            self.departement_id = False
        if not self._country_level("commune"):
            self.commune_id = False
        if not self._country_level("quartier"):
            self.quartier_id = False

    def _geo_domains(self):
        self.ensure_one()
        return {
            "region_id": self._geo_domain("region"),
            "departement_id": self._geo_domain("department"),
            "commune_id": self._geo_domain("commune"),
            "quartier_id": self._geo_domain("quartier"),
        }

    def _geo_is_descendant_of(self, record, ancestor):
        if not record or not ancestor:
            return False
        current = record
        seen = set()
        while current and current.id not in seen:
            if current == ancestor:
                return True
            seen.add(current.id)
            current = current.parent_id
        return False

    def _required_local_roles(self):
        self.ensure_one()
        if self.type_section == "regionale":
            return ["region"]
        if self.type_section == "departementale":
            return ["department"]
        if self.type_section == "communale":
            roles = []
            for role in ("region", "department", "commune"):
                if self._country_level(role):
                    roles.append(role)
            if self._country_level("quartier"):
                roles.append("quartier")
            return roles
        return []

    @api.onchange("country_id", "type_section")
    def _onchange_country_and_type(self):
        self._clear_incompatible_geography()
        if self.type_section in ("nationale", "diaspora"):
            self.region_id = False
            self.departement_id = False
            self.commune_id = False
            self.quartier_id = False
        return {"domain": self._geo_domains()}

    @api.onchange("region_id")
    def _onchange_region_id(self):
        if self.departement_id and self._country_level("department"):
            if not self._geo_is_descendant_of(self.departement_id, self.region_id):
                self.departement_id = False

        if self.commune_id and self._country_level("commune"):
            parent = self.departement_id if self._country_level("department") else self.region_id
            if parent and not self._geo_is_descendant_of(self.commune_id, parent):
                self.commune_id = False

        if self.quartier_id and self._country_level("quartier"):
            parent = self.commune_id or self.departement_id or self.region_id
            if not parent or not self._geo_is_descendant_of(self.quartier_id, parent):
                self.quartier_id = False

        return {"domain": self._geo_domains()}

    @api.onchange("departement_id")
    def _onchange_departement_id(self):
        if self.commune_id and self._country_level("commune"):
            parent = self.departement_id if self._country_level("department") else self.region_id
            if parent and not self._geo_is_descendant_of(self.commune_id, parent):
                self.commune_id = False
            elif not parent:
                self.commune_id = False

        if self.quartier_id and self._country_level("quartier"):
            parent = self.commune_id or self.departement_id or self.region_id
            if parent and not self._geo_is_descendant_of(self.quartier_id, parent):
                self.quartier_id = False
            elif not parent:
                self.quartier_id = False

        return {"domain": self._geo_domains()}

    @api.onchange("commune_id")
    def _onchange_commune_id(self):
        if self.quartier_id and self._country_level("quartier"):
            parent = self.commune_id or self.departement_id or self.region_id
            if parent and not self._geo_is_descendant_of(self.quartier_id, parent):
                self.quartier_id = False
            elif not parent:
                self.quartier_id = False
        return {"domain": self._geo_domains()}

    @api.constrains(
        "country_id",
        "type_section",
        "region_id",
        "departement_id",
        "commune_id",
        "quartier_id",
    )
    def _check_geography(self):
        """Validate geography using the country-specific conceptual mapping."""
        for record in self:
            if record.type_section in ("nationale", "diaspora"):
                continue

            roles = record._required_local_roles()
            field_by_role = {
                "region": record.region_id,
                "department": record.departement_id,
                "commune": record.commune_id,
                "quartier": record.quartier_id,
            }

            if record.type_section in ("regionale", "departementale", "communale") and not roles:
                raise ValidationError(
                    _("Aucun niveau géographique correspondant n'est configuré pour le pays %s.")
                    % record.country_id.name
                )

            labels = {
                "region": record.country_id.kiiraaye_geo_region_label,
                "department": record.country_id.kiiraaye_geo_department_label,
                "commune": record.country_id.kiiraaye_geo_commune_label,
                "quartier": record.country_id.kiiraaye_geo_quartier_label,
            }

            for role in roles:
                if not field_by_role[role]:
                    raise ValidationError(
                        _("Le champ %s est obligatoire pour ce type de structure et ce pays.")
                        % (labels.get(role) or role.title())
                    )

            for role, value in field_by_role.items():
                expected_level = record._country_level(role)
                if not value:
                    continue
                if value.country_id != record.country_id or value.niveau != expected_level:
                    raise ValidationError(
                        _("La valeur %s ne correspond pas au niveau géographique configuré pour le pays sélectionné.")
                        % role
                    )

            parent_checks = [
                (
                    record.departement_id,
                    record.region_id,
                    "Le département doit appartenir à la région sélectionnée.",
                ),
                (
                    record.commune_id,
                    record.departement_id or record.region_id,
                    "La commune doit appartenir au niveau administratif parent sélectionné.",
                ),
                (
                    record.quartier_id,
                    record.commune_id or record.departement_id or record.region_id,
                    "Le quartier doit appartenir au niveau administratif parent sélectionné.",
                ),
            ]
            for value, parent, message in parent_checks:
                if value and parent and not record._geo_is_descendant_of(value, parent):
                    raise ValidationError(_(message))

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get("type_section") in ("nationale", "diaspora"):
                vals.update({
                    "region_id": False,
                    "departement_id": False,
                    "commune_id": False,
                    "quartier_id": False,
                })
        return super().create(vals_list)
