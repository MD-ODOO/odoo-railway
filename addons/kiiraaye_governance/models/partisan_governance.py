from odoo import api, fields, models, _
from odoo.exceptions import UserError


class KiiraayePartisanGovernance(models.Model):
    _inherit = "kiiraaye.partisan"

    coordonnateur_banner = fields.Char(
        string="Coordonnateur de section(s)",
        compute="_compute_coordonnateur_banner",
    )

    @api.depends("section_ids.cordonnateur_id", "section_ids.name")
    def _compute_coordonnateur_banner(self):
        for record in self:
            sections = record.section_ids.filtered(
                lambda section: section.cordonnateur_id == record
            )
            record.coordonnateur_banner = " • ".join(
                f"{section.name}" for section in sections if section.name
            )

    user_id = fields.Many2one(
        "res.users",
        string="Utilisateur Odoo",
        copy=False,
        ondelete="set null",
        index=True,
        groups="kiiraaye_governance.group_kiiraaye_manager",
    )
    region_id = fields.Many2one(
        "kiiraaye.geographie",
        string="Région",
        ondelete="restrict",
        index=True,
    )
    departement_id = fields.Many2one(
        "kiiraaye.geographie",
        string="Département",
        ondelete="restrict",
        index=True,
    )
    commune_id = fields.Many2one(
        "kiiraaye.geographie",
        string="Commune",
        ondelete="restrict",
        index=True,
    )
    quartier_id = fields.Many2one(
        "kiiraaye.geographie",
        string="Quartier",
        ondelete="restrict",
        index=True,
    )

    _unique_user_id_governance = models.Constraint(
        "UNIQUE(user_id)",
        "Un utilisateur Odoo ne peut être associé qu'à un seul membre Kiiraaye.",
    )

    @api.model
    def _get_connected_coordinator_sections(self):
        user = self.env.user
        domain = [("active", "=", True), ("state", "=", "ouverte")]
        if user.has_group("kiiraaye_governance.group_kiiraaye_manager"):
            return self.env["kiiraaye.section"].sudo().search(domain, order="name, id")
        if user.kiiraaye_role == "national":
            return self.env["kiiraaye.section"].sudo().search(domain, order="name, id")
        if user.kiiraaye_role == "regional":
            domain.append(("region_id", "in", user.kiiraaye_coordinator_region_ids.ids))
        elif user.kiiraaye_role == "departemental":
            domain.append(("departement_id", "in", user.kiiraaye_coordinator_departement_ids.ids))
        elif user.kiiraaye_role == "communal":
            domain.append(("commune_id", "in", user.kiiraaye_coordinator_commune_ids.ids))
        elif user.kiiraaye_role == "quartier":
            domain.append(("quartier_id", "in", user.kiiraaye_coordinator_quartier_ids.ids))
        else:
            return self.env["kiiraaye.section"].browse()
        return self.env["kiiraaye.section"].sudo().search(domain, order="name, id")

    @api.model
    def _get_default_coordinator_section(self):
        sections = self._get_connected_coordinator_sections()
        return sections[:1] if sections else self.env["kiiraaye.section"]

    @api.model
    def default_get(self, fields_list):
        vals = super().default_get(fields_list)
        user = self.env.user
        if user.has_group("kiiraaye_governance.group_kiiraaye_manager") or not user.kiiraaye_role:
            return vals
        vals.update({
            "country_id": user.kiiraaye_country_id.id,
            "region_id": user.kiiraaye_region_id.id,
            "departement_id": user.kiiraaye_departement_id.id,
            "commune_id": user.kiiraaye_commune_id.id,
            "quartier_id": user.kiiraaye_quartier_id.id,
        })
        sections = self._get_connected_coordinator_sections()
        # Si le périmètre ne contient qu'une section, elle est proposée automatiquement.
        if len(sections) == 1:
            vals["section_ids"] = [(6, 0, sections.ids)]
        return vals

    @api.onchange("country_id")
    def _onchange_governance_country_id(self):
        self.region_id = False
        self.departement_id = False
        self.commune_id = False
        self.quartier_id = False
        return {
            "domain": {
                "region_id": (
                    [
                        ("country_id", "=", self.country_id.id),
                        ("niveau", "=", "niveau1"),
                        ("active", "=", True),
                    ]
                    if self.country_id
                    else [("id", "=", False)]
                ),
                "section_ids": (
                    [
                        ("country_id", "=", self.country_id.id),
                        ("active", "=", True),
                        ("state", "=", "ouverte"),
                    ]
                    if self.country_id
                    else [("id", "=", False)]
                ),
                "departement_id": [("id", "=", False)],
                "commune_id": [("id", "=", False)],
                "quartier_id": [("id", "=", False)],
            }
        }

    @api.onchange("region_id")
    def _onchange_governance_region_id(self):
        if self.departement_id and self.departement_id.parent_id != self.region_id:
            self.departement_id = False
            self.commune_id = False
            self.quartier_id = False
        elif not self.region_id:
            self.departement_id = False
            self.commune_id = False
            self.quartier_id = False

        return {
            "domain": {
                "departement_id": [
                    ("country_id", "=", self.country_id.id),
                    ("niveau", "=", "niveau2"),
                    ("parent_id", "=", self.region_id.id or False),
                    ("active", "=", True),
                ]
            }
        }

    @api.onchange("departement_id")
    def _onchange_governance_departement_id(self):
        if self.commune_id and self.commune_id.parent_id != self.departement_id:
            self.commune_id = False
            self.quartier_id = False
        elif not self.departement_id:
            self.commune_id = False
            self.quartier_id = False

        return {
            "domain": {
                "commune_id": [
                    ("country_id", "=", self.country_id.id),
                    ("niveau", "=", "niveau3"),
                    ("parent_id", "=", self.departement_id.id or False),
                    ("active", "=", True),
                ]
            }
        }

    @api.onchange("commune_id")
    def _onchange_governance_commune_id(self):
        if self.quartier_id and self.commune_id:
            current = self.quartier_id
            valid = False
            while current:
                if current.parent_id == self.commune_id:
                    valid = True
                    break
                current = current.parent_id
            if not valid:
                self.quartier_id = False
        elif not self.commune_id:
            self.quartier_id = False

        return {
            "domain": {
                "quartier_id": (
                    [
                        ("country_id", "=", self.country_id.id),
                        ("niveau", "=", "niveau5"),
                        ("parent_id", "child_of", self.commune_id.id),
                        ("active", "=", True),
                    ]
                    if self.commune_id
                    else [("id", "=", False)]
                )
            }
        }

    def _apply_coordinator_scope_on_create(self, vals):
        if self.env.user.has_group("kiiraaye_governance.group_kiiraaye_manager"):
            return

        user = self.env.user
        if not user.kiiraaye_role:
            raise UserError(_("Votre utilisateur n'a pas de fonction Kiiraaye configurée."))

        sections = self._get_connected_coordinator_sections()
        allowed_ids = set(sections.ids)
        selected_ids = set()
        for command in vals.get("section_ids") or []:
            if isinstance(command, (list, tuple)) and command:
                if command[0] == 6:
                    selected_ids.update(command[2] or [])
                elif command[0] == 4:
                    selected_ids.add(command[1])

        if selected_ids and not selected_ids.issubset(allowed_ids):
            raise UserError(_("Vous ne pouvez rattacher un membre qu'à une section de votre périmètre."))

        if len(selected_ids) == 1:
            section = self.env["kiiraaye.section"].browse(next(iter(selected_ids)))
            vals.update({
                "country_id": section.country_id.id,
                "region_id": section.region_id.id,
                "departement_id": section.departement_id.id,
                "commune_id": section.commune_id.id,
                "quartier_id": section.quartier_id.id,
            })
        else:
            vals.setdefault("country_id", user.kiiraaye_country_id.id)
            vals.setdefault("region_id", user.kiiraaye_region_id.id)
            vals.setdefault("departement_id", user.kiiraaye_departement_id.id)
            vals.setdefault("commune_id", user.kiiraaye_commune_id.id)
            vals.setdefault("quartier_id", user.kiiraaye_quartier_id.id)

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if self.env.context.get("kiiraaye_demo_generation"):
                vals["is_demo_data"] = True
            if not vals.get("reference") or vals.get("reference") == "Nouveau":
                vals["reference"] = self.env["ir.sequence"].next_by_code(
                    "kiiraaye.partisan"
                )
                if not vals["reference"]:
                    raise UserError(
                        _("La séquence du numéro de membre Kiiraaye est introuvable.")
                    )

            if not vals.get("national_id"):
                vals["national_id"] = False

            if not self.env.context.get("kiiraaye_demo_generation"):
                self._apply_coordinator_scope_on_create(vals)

        records = super().create(vals_list)
        self.env["kiiraaye.section"].sudo()._sync_coordinator_access()
        return records

    def write(self, vals):
        self._check_coordinator_scope_on_write(vals)

        if "national_id" in vals and not vals.get("national_id"):
            vals["national_id"] = False

        result = super().write(vals)
        if "user_id" in vals:
            self.env["kiiraaye.section"].sudo()._sync_coordinator_access()
        return result
