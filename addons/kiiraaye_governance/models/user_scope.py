from odoo import api, fields, models, _
from odoo.exceptions import ValidationError


class ResUsers(models.Model):
    _inherit = "res.users"

    kiiraaye_role = fields.Selection(
        [
            ("national", "Mandataire national / Coordonnateur national"),
            ("regional", "Coordonnateur régional"),
            ("departemental", "Coordonnateur départemental"),
            ("communal", "Coordonnateur communal"),
            ("quartier", "Coordonnateur de quartier"),
        ],
        string="Fonction Kiiraaye",
        copy=False,
        index=True,
        groups="kiiraaye_governance.group_kiiraaye_manager",
    )
    kiiraaye_country_id = fields.Many2one(
        "res.country",
        string="Pays",
        copy=False,
        ondelete="restrict",
        default=lambda self: self.env["res.country"].search([("code", "=", "SN")], limit=1),
        domain=[("code", "=", "SN")],
        groups="kiiraaye_governance.group_kiiraaye_manager",
    )
    kiiraaye_region_id = fields.Many2one(
        "kiiraaye.geographie",
        string="Région",
        copy=False,
        ondelete="restrict",
        domain="[('country_id', '=', kiiraaye_country_id), ('niveau', '=', 'niveau1'), ('active', '=', True)]",
        groups="kiiraaye_governance.group_kiiraaye_manager",
    )
    kiiraaye_departement_id = fields.Many2one(
        "kiiraaye.geographie",
        string="Département",
        copy=False,
        ondelete="restrict",
        domain="[('country_id', '=', kiiraaye_country_id), ('niveau', '=', 'niveau2'), ('parent_id', '=', kiiraaye_region_id), ('active', '=', True)]",
        groups="kiiraaye_governance.group_kiiraaye_manager",
    )
    kiiraaye_commune_id = fields.Many2one(
        "kiiraaye.geographie",
        string="Commune",
        copy=False,
        ondelete="restrict",
        domain="[('country_id', '=', kiiraaye_country_id), ('niveau', '=', 'niveau3'), ('parent_id', '=', kiiraaye_departement_id), ('active', '=', True)]",
        groups="kiiraaye_governance.group_kiiraaye_manager",
    )
    kiiraaye_quartier_id = fields.Many2one(
        "kiiraaye.geographie",
        string="Quartier",
        copy=False,
        ondelete="restrict",
        domain="[('country_id', '=', kiiraaye_country_id), ('niveau', '=', 'niveau5'), ('parent_id', 'child_of', kiiraaye_commune_id), ('active', '=', True)]",
        groups="kiiraaye_governance.group_kiiraaye_manager",
    )

    kiiraaye_partisan_id = fields.Many2one(
        "kiiraaye.partisan", string="Membre Kiiraaye",
        compute="_compute_kiiraaye_scope", compute_sudo=True,
    )
    kiiraaye_coordinator_section_ids = fields.Many2many(
        "kiiraaye.section", string="Sections visibles Kiiraaye",
        compute="_compute_kiiraaye_scope", compute_sudo=True,
    )
    kiiraaye_coordinator_region_ids = fields.Many2many(
        "kiiraaye.geographie", string="Régions autorisées Kiiraaye",
        compute="_compute_kiiraaye_scope", compute_sudo=True,
    )
    kiiraaye_coordinator_departement_ids = fields.Many2many(
        "kiiraaye.geographie", string="Départements autorisés Kiiraaye",
        compute="_compute_kiiraaye_scope", compute_sudo=True,
    )
    kiiraaye_coordinator_commune_ids = fields.Many2many(
        "kiiraaye.geographie", string="Communes autorisées Kiiraaye",
        compute="_compute_kiiraaye_scope", compute_sudo=True,
    )
    kiiraaye_coordinator_quartier_ids = fields.Many2many(
        "kiiraaye.geographie", string="Quartiers autorisés Kiiraaye",
        compute="_compute_kiiraaye_scope", compute_sudo=True,
    )

    @api.onchange("kiiraaye_role")
    def _onchange_kiiraaye_role(self):
        if self.kiiraaye_role:
            self.kiiraaye_country_id = self.env["res.country"].search([("code", "=", "SN")], limit=1)
        if self.kiiraaye_role == "national":
            self.kiiraaye_region_id = False
            self.kiiraaye_departement_id = False
            self.kiiraaye_commune_id = False
            self.kiiraaye_quartier_id = False
        elif self.kiiraaye_role == "regional":
            self.kiiraaye_departement_id = False
            self.kiiraaye_commune_id = False
            self.kiiraaye_quartier_id = False
        elif self.kiiraaye_role == "departemental":
            self.kiiraaye_commune_id = False
            self.kiiraaye_quartier_id = False
        elif self.kiiraaye_role == "communal":
            self.kiiraaye_quartier_id = False
        else:
            self.kiiraaye_region_id = False
            self.kiiraaye_departement_id = False
            self.kiiraaye_commune_id = False
            self.kiiraaye_quartier_id = False

    @api.onchange("kiiraaye_region_id")
    def _onchange_kiiraaye_region_id(self):
        if self.kiiraaye_departement_id and self.kiiraaye_departement_id.parent_id != self.kiiraaye_region_id:
            self.kiiraaye_departement_id = False
            self.kiiraaye_commune_id = False
            self.kiiraaye_quartier_id = False
        elif not self.kiiraaye_region_id:
            self.kiiraaye_departement_id = False
            self.kiiraaye_commune_id = False
            self.kiiraaye_quartier_id = False

    @api.onchange("kiiraaye_departement_id")
    def _onchange_kiiraaye_departement_id(self):
        if self.kiiraaye_commune_id and self.kiiraaye_commune_id.parent_id != self.kiiraaye_departement_id:
            self.kiiraaye_commune_id = False
            self.kiiraaye_quartier_id = False
        elif not self.kiiraaye_departement_id:
            self.kiiraaye_commune_id = False
            self.kiiraaye_quartier_id = False

    @api.onchange("kiiraaye_commune_id")
    def _onchange_kiiraaye_commune_id(self):
        if self.kiiraaye_quartier_id and self.kiiraaye_commune_id:
            current = self.kiiraaye_quartier_id
            valid = False
            while current:
                if current.parent_id == self.kiiraaye_commune_id:
                    valid = True
                    break
                current = current.parent_id
            if not valid:
                self.kiiraaye_quartier_id = False
        elif not self.kiiraaye_commune_id:
            self.kiiraaye_quartier_id = False

    def _normalize_kiiraaye_scope_vals(self, vals):
        role = vals.get("kiiraaye_role")
        if not role:
            return
        senegal = self.env["res.country"].search([("code", "=", "SN")], limit=1)
        vals["kiiraaye_country_id"] = senegal.id if senegal else False
        if role == "national":
            vals.update({"kiiraaye_region_id": False, "kiiraaye_departement_id": False, "kiiraaye_commune_id": False, "kiiraaye_quartier_id": False})
        elif role == "regional":
            vals.update({"kiiraaye_departement_id": False, "kiiraaye_commune_id": False, "kiiraaye_quartier_id": False})
        elif role == "departemental":
            vals.update({"kiiraaye_commune_id": False, "kiiraaye_quartier_id": False})
        elif role == "communal":
            vals.update({"kiiraaye_quartier_id": False})

    @api.constrains("kiiraaye_role", "kiiraaye_country_id", "kiiraaye_region_id", "kiiraaye_departement_id", "kiiraaye_commune_id", "kiiraaye_quartier_id")
    def _check_kiiraaye_scope(self):
        for user in self:
            if not user.kiiraaye_role:
                continue
            if not user.kiiraaye_country_id or user.kiiraaye_country_id.code != "SN":
                raise ValidationError(_("Un utilisateur Kiiraaye doit avoir le pays Sénégal."))
            role = user.kiiraaye_role
            if role == "regional" and not user.kiiraaye_region_id:
                raise ValidationError(_("Le coordonnateur régional doit avoir une région."))
            if role == "departemental" and (not user.kiiraaye_region_id or not user.kiiraaye_departement_id):
                raise ValidationError(_("Le coordonnateur départemental doit avoir une région et un département."))
            if role == "communal" and (not user.kiiraaye_region_id or not user.kiiraaye_departement_id or not user.kiiraaye_commune_id):
                raise ValidationError(_("Le coordonnateur communal doit avoir une région, un département et une commune."))
            if role == "quartier" and (not user.kiiraaye_region_id or not user.kiiraaye_departement_id or not user.kiiraaye_commune_id or not user.kiiraaye_quartier_id):
                raise ValidationError(_("Le coordonnateur de quartier doit avoir une région, un département, une commune et un quartier."))
            if role == "national" and any((user.kiiraaye_region_id, user.kiiraaye_departement_id, user.kiiraaye_commune_id, user.kiiraaye_quartier_id)):
                raise ValidationError(_("Le coordonnateur national ne doit pas avoir de niveau territorial inférieur au pays."))
            if user.kiiraaye_region_id and (user.kiiraaye_region_id.country_id != user.kiiraaye_country_id or user.kiiraaye_region_id.niveau != "niveau1"):
                raise ValidationError(_("La région du coordonnateur est invalide."))
            if user.kiiraaye_departement_id and (user.kiiraaye_departement_id.country_id != user.kiiraaye_country_id or user.kiiraaye_departement_id.niveau != "niveau2" or user.kiiraaye_departement_id.parent_id != user.kiiraaye_region_id):
                raise ValidationError(_("Le département doit appartenir à la région sélectionnée."))
            if user.kiiraaye_commune_id and (user.kiiraaye_commune_id.country_id != user.kiiraaye_country_id or user.kiiraaye_commune_id.niveau != "niveau3" or user.kiiraaye_commune_id.parent_id != user.kiiraaye_departement_id):
                raise ValidationError(_("La commune doit appartenir au département sélectionné."))
            if user.kiiraaye_quartier_id:
                if user.kiiraaye_quartier_id.country_id != user.kiiraaye_country_id or user.kiiraaye_quartier_id.niveau != "niveau5":
                    raise ValidationError(_("Le quartier sélectionné est invalide."))
                current = user.kiiraaye_quartier_id
                valid = False
                while current:
                    if current.parent_id == user.kiiraaye_commune_id:
                        valid = True
                        break
                    current = current.parent_id
                if not valid:
                    raise ValidationError(_("Le quartier doit appartenir à la commune sélectionnée."))

    def _compute_kiiraaye_scope(self):
        Geography = self.env["kiiraaye.geographie"].sudo()
        Section = self.env["kiiraaye.section"].sudo()
        Partisan = self.env["kiiraaye.partisan"].sudo()
        senegal = self.env["res.country"].sudo().search([("code", "=", "SN")], limit=1)
        for user in self:
            regions = Geography.browse()
            departments = Geography.browse()
            communes = Geography.browse()
            quartiers = Geography.browse()
            role = user.kiiraaye_role
            if role == "national":
                base = [("active", "=", True)] + ([ ("country_id", "=", senegal.id) ] if senegal else [])
                regions = Geography.search(base + [("niveau", "=", "niveau1")])
                departments = Geography.search(base + [("niveau", "=", "niveau2")])
                communes = Geography.search(base + [("niveau", "=", "niveau3")])
                quartiers = Geography.search(base + [("niveau", "=", "niveau5")])
                sections = Section.search([("active", "=", True), ("state", "=", "ouverte")])
            elif role == "regional" and user.kiiraaye_region_id:
                regions = user.kiiraaye_region_id
                departments = Geography.search([("id", "child_of", regions.ids), ("niveau", "=", "niveau2"), ("active", "=", True)])
                communes = Geography.search([("id", "child_of", departments.ids), ("niveau", "=", "niveau3"), ("active", "=", True)])
                quartiers = Geography.search([("id", "child_of", communes.ids), ("niveau", "=", "niveau5"), ("active", "=", True)])
                sections = Section.search([("active", "=", True), ("state", "=", "ouverte"), "|", "|", "|", ("region_id", "in", regions.ids), ("departement_id", "in", departments.ids), ("commune_id", "in", communes.ids), ("quartier_id", "in", quartiers.ids)])
            elif role == "departemental" and user.kiiraaye_departement_id:
                regions = user.kiiraaye_region_id
                departments = user.kiiraaye_departement_id
                communes = Geography.search([("id", "child_of", departments.ids), ("niveau", "=", "niveau3"), ("active", "=", True)])
                quartiers = Geography.search([("id", "child_of", communes.ids), ("niveau", "=", "niveau5"), ("active", "=", True)])
                sections = Section.search([("active", "=", True), ("state", "=", "ouverte"), "|", "|", ("departement_id", "in", departments.ids), ("commune_id", "in", communes.ids), ("quartier_id", "in", quartiers.ids)])
            elif role == "communal" and user.kiiraaye_commune_id:
                regions = user.kiiraaye_region_id
                departments = user.kiiraaye_departement_id
                communes = user.kiiraaye_commune_id
                quartiers = Geography.search([("id", "child_of", communes.ids), ("niveau", "=", "niveau5"), ("active", "=", True)])
                sections = Section.search([("active", "=", True), ("state", "=", "ouverte"), "|", ("commune_id", "in", communes.ids), ("quartier_id", "in", quartiers.ids)])
            elif role == "quartier" and user.kiiraaye_quartier_id:
                regions = user.kiiraaye_region_id
                departments = user.kiiraaye_departement_id
                communes = user.kiiraaye_commune_id
                quartiers = user.kiiraaye_quartier_id
                sections = Section.search([("active", "=", True), ("state", "=", "ouverte"), ("quartier_id", "in", quartiers.ids)])
            else:
                sections = Section.browse()
            user.kiiraaye_partisan_id = Partisan.search([("user_id", "=", user.id)], limit=1)
            user.kiiraaye_coordinator_section_ids = sections
            user.kiiraaye_coordinator_region_ids = regions
            user.kiiraaye_coordinator_departement_ids = departments
            user.kiiraaye_coordinator_commune_ids = communes
            user.kiiraaye_coordinator_quartier_ids = quartiers

    def _sync_kiiraaye_role_group(self):
        coordinator = self.env.ref("kiiraaye_governance.group_kiiraaye_coordinator", raise_if_not_found=False)
        national = self.env.ref("kiiraaye_governance.group_kiiraaye_national_coordinator", raise_if_not_found=False)
        if not coordinator or not national:
            return
        for user in self:
            if user.kiiraaye_role == "national":
                commands = [Command.link(national.id), Command.unlink(coordinator.id)]
            elif user.kiiraaye_role in ("regional", "departemental", "communal", "quartier"):
                commands = [Command.link(coordinator.id), Command.unlink(national.id)]
            else:
                commands = [Command.unlink(coordinator.id), Command.unlink(national.id)]
            user.with_context(kiiraaye_skip_role_sync=True).write({"group_ids": commands})

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            self._normalize_kiiraaye_scope_vals(vals)
        records = super().create(vals_list)
        records._sync_kiiraaye_role_group()
        return records

    def write(self, vals):
        vals = dict(vals)
        changed = "kiiraaye_role" in vals or any(
            field in vals for field in (
                "kiiraaye_country_id", "kiiraaye_region_id", "kiiraaye_departement_id",
                "kiiraaye_commune_id", "kiiraaye_quartier_id"
            )
        )
        if "kiiraaye_role" in vals:
            self._normalize_kiiraaye_scope_vals(vals)
        result = super().write(vals)
        if changed and not self.env.context.get("kiiraaye_skip_role_sync"):
            self._sync_kiiraaye_role_group()
        return result
