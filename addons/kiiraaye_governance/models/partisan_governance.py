from odoo import api, fields, models, _
from odoo.exceptions import UserError


class KiiraayePartisanGovernance(models.Model):
    _inherit = "kiiraaye.partisan"

    user_id = fields.Many2one("res.users", string="Utilisateur Odoo", copy=False, ondelete="set null", index=True, groups="kiiraaye_governance.group_kiiraaye_manager")
    region_id = fields.Many2one("kiiraaye.geographie", string="Région", ondelete="restrict", index=True)
    departement_id = fields.Many2one("kiiraaye.geographie", string="Département", ondelete="restrict", index=True)
    commune_id = fields.Many2one("kiiraaye.geographie", string="Commune", ondelete="restrict", index=True)
    quartier_id = fields.Many2one("kiiraaye.geographie", string="Quartier", ondelete="restrict", index=True)

    _unique_user_id_governance = models.Constraint("UNIQUE(user_id)", "Un utilisateur Odoo ne peut être associé qu'à un seul membre Kiiraaye.")

    @api.model
    def _get_connected_coordinator_sections(self):
        return self.env["kiiraaye.section"].sudo().search([
            ("cordonnateur_id.user_id", "=", self.env.user.id),
            ("active", "=", True),
            ("state", "=", "ouverte"),
        ], order="id")

    @api.model
    def _get_default_coordinator_section(self):
        sections = self._get_connected_coordinator_sections()
        if not sections:
            return self.env["kiiraaye.section"]
        priority = {"regionale": 1, "departementale": 2, "communale": 3, "nationale": 4, "diaspora": 5}
        return sorted(sections, key=lambda s: priority.get(s.type_section, 99))[0]

    @api.model
    def default_get(self, fields_list):
        vals = super().default_get(fields_list)
        if self.env.user.has_group("kiiraaye_governance.group_kiiraaye_manager"):
            return vals
        section = self._get_default_coordinator_section()
        if not section:
            return vals
        vals.update({
            "country_id": section.country_id.id,
            "section_ids": [(6, 0, [section.id])],
            "region_id": section.region_id.id,
            "departement_id": section.departement_id.id,
            "commune_id": section.commune_id.id,
            "quartier_id": section.quartier_id.id,
        })
        return vals

    @api.onchange("section_ids")
    def _onchange_governance_section_ids(self):
        section = self.section_ids[:1]
        if not section:
            self.region_id = False
            self.departement_id = False
            self.commune_id = False
            self.quartier_id = False
            return
        self.country_id = section.country_id
        self.region_id = section.region_id
        self.departement_id = section.departement_id
        self.commune_id = section.commune_id
        self.quartier_id = section.quartier_id

    @api.onchange("region_id")
    def _onchange_governance_region_id(self):
        if self.departement_id and self.departement_id.parent_id != self.region_id:
            self.departement_id = False
            self.commune_id = False
            self.quartier_id = False
        return {"domain": {"departement_id": [
            ("country_id", "=", self.country_id.id), ("niveau", "=", "niveau2"),
            ("parent_id", "=", self.region_id.id or False), ("active", "=", True),
        ]}}

    @api.onchange("departement_id")
    def _onchange_governance_departement_id(self):
        if self.commune_id and self.commune_id.parent_id != self.departement_id:
            self.commune_id = False
            self.quartier_id = False
        return {"domain": {"commune_id": [
            ("country_id", "=", self.country_id.id), ("niveau", "=", "niveau3"),
            ("parent_id", "=", self.departement_id.id or False), ("active", "=", True),
        ]}}

    @api.onchange("commune_id")
    def _onchange_governance_commune_id(self):
        if self.quartier_id and self.quartier_id.parent_id != self.commune_id:
            self.quartier_id = False
        return {"domain": {"quartier_id": (
            [("country_id", "=", self.country_id.id), ("niveau", "=", "niveau5"),
             ("parent_id", "=", self.commune_id.id), ("active", "=", True)]
            if self.commune_id else [("id", "=", False)]
        )}}

    def _apply_coordinator_scope_on_create(self, vals):
        if self.env.user.has_group("kiiraaye_governance.group_kiiraaye_manager"):
            return
        sections = self._get_connected_coordinator_sections()
        if not sections:
            raise UserError(_("Seul le coordonnateur connecté d'une section ouverte peut créer un membre."))
        allowed_ids = set(sections.ids)
        selected_ids = set()
        for command in vals.get("section_ids") or []:
            if isinstance(command, (list, tuple)) and command:
                if command[0] == 6:
                    selected_ids.update(command[2] or [])
                elif command[0] == 4:
                    selected_ids.add(command[1])
        selected_ids &= allowed_ids
        section = sections.filtered(lambda s: s.id in selected_ids)[:1] if selected_ids else self._get_default_coordinator_section()
        vals["section_ids"] = [(6, 0, [section.id])]
        vals.update({
            "country_id": section.country_id.id,
            "region_id": section.region_id.id,
            "departement_id": section.departement_id.id,
            "commune_id": section.commune_id.id,
            "quartier_id": section.quartier_id.id,
        })

    def _check_coordinator_scope_on_write(self, vals):
        if self.env.user.has_group("kiiraaye_governance.group_kiiraaye_manager"):
            return
        sections = self._get_connected_coordinator_sections()
        if not sections:
            raise UserError(_("Vous n'êtes pas coordonnateur d'une section ouverte."))
        allowed_ids = set(sections.ids)
        if "section_ids" in vals:
            selected_ids = set()
            for command in vals.get("section_ids") or []:
                if isinstance(command, (list, tuple)) and command:
                    if command[0] == 6:
                        selected_ids.update(command[2] or [])
                    elif command[0] == 4:
                        selected_ids.add(command[1])
            if selected_ids and not selected_ids.issubset(allowed_ids):
                raise UserError(_("Vous ne pouvez rattacher un membre qu'à vos sections coordonnées."))
        for record in self:
            region_id = vals.get("region_id", record.region_id.id)
            departement_id = vals.get("departement_id", record.departement_id.id)
            commune_id = vals.get("commune_id", record.commune_id.id)
            quartier_id = vals.get("quartier_id", record.quartier_id.id)
            allowed = False
            for section in sections:
                if section.type_section == "regionale" and section.region_id.id == region_id:
                    allowed = True
                elif section.type_section == "departementale" and section.departement_id.id == departement_id:
                    allowed = True
                elif section.type_section == "communale" and section.quartier_id.id == quartier_id:
                    allowed = True
                if allowed:
                    break
            if not allowed:
                raise UserError(_("Vous ne pouvez modifier ce membre qu'à l'intérieur de votre zone de coordination."))

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if not vals.get("reference") or vals.get("reference") == "Nouveau":
                vals["reference"] = self.env["ir.sequence"].next_by_code("kiiraaye.partisan")
                if not vals["reference"]:
                    raise UserError(_("La séquence du numéro de membre Kiiraaye est introuvable."))
            if not vals.get("national_id"):
                vals["national_id"] = False
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
