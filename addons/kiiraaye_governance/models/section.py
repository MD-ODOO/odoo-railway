from odoo import api, fields, models, _
from odoo.exceptions import ValidationError


class KiiraayeSection(models.Model):
    _name = "kiiraaye.section"
    _description = "Section / Coordination Kiiraaye"
    _rec_name = "name"
    _order = "name, id"

    name = fields.Char(string="Nom", readonly=True, compute="_compute_name", store=True, index=True, help="Nom généré automatiquement à partir du type et de la hiérarchie géographique.")
    reference = fields.Char(string="Référence", required=True, copy=False, readonly=True, default=lambda self: self.env["ir.sequence"].next_by_code("kiiraaye.section") or "Nouveau")
    type_section = fields.Selection([("communale", "Section communale"), ("departementale", "Coordination départementale"), ("regionale", "Coordination régionale"), ("nationale", "Coordination nationale"), ("diaspora", "Coordination diaspora")], string="Type de section / coordination", required=True)
    country_id = fields.Many2one("res.country", string="Pays", required=True, default=lambda self: self._default_senegal(), ondelete="restrict")

    region_id = fields.Many2one("kiiraaye.geographie", string="Région", ondelete="restrict")
    departement_id = fields.Many2one("kiiraaye.geographie", string="Département", ondelete="restrict")
    commune_id = fields.Many2one("kiiraaye.geographie", string="Commune", ondelete="restrict")
    quartier_id = fields.Many2one("kiiraaye.geographie", string="Quartier", ondelete="restrict")
    siege_partner_id = fields.Many2one("res.partner", string="Siège / Adresse", ondelete="restrict", copy=False, help="Adresse du siège gérée avec le formulaire d'adresse natif d'Odoo.")
    date_creation = fields.Date(string="Date de création", default=fields.Date.context_today)
    state = fields.Selection([("ouverte", "Ouverte"), ("fermee", "Fermée")], string="État", required=True, default="ouverte")
    active = fields.Boolean(string="Actif", default=True)
    is_demo_data = fields.Boolean(string="Donnée de démonstration", default=False, copy=False, index=True)
    member_count = fields.Integer(string="Nombre de membres", compute="_compute_member_count")
    member_status_id = fields.Many2one("kiiraaye.effectif.status", string="Statut d'effectif", compute="_compute_member_status")

    @api.depends("membre_ids")
    def _compute_member_count(self):
        for record in self:
            record.member_count = len(record.membre_ids)

    @api.depends("member_count")
    def _compute_member_status(self):
        Status = self.env["kiiraaye.effectif.status"]
        for record in self:
            record.member_status_id = Status.get_for_count(record.member_count)

    membre_ids = fields.Many2many("kiiraaye.partisan", "kiiraaye_section_partisan_rel", "section_id", "partisan_id", string="Membres")
    bureau_ligne_ids = fields.One2many("kiiraaye.bureau.ligne", "section_id", string="Membres du bureau", copy=True)

    hierarchy_anchor = fields.Boolean(
        string="Hiérarchie",
        compute="_compute_hierarchy_anchor",
        readonly=True,
        help="Champ utilisé pour afficher le widget de hiérarchie OWL",
    )

    @api.depends("id")
    def _compute_hierarchy_anchor(self):
        for record in self:
            record.hierarchy_anchor = bool(record.id)

    def _compute_name(self):
        type_labels = dict(self._fields["type_section"].selection)
        for record in self:
            parts = [type_labels.get(record.type_section, record.type_section or _("Section / Coordination Kiiraaye"))]
            for field_name in ("region_id", "departement_id", "commune_id", "quartier_id"):
                value = getattr(record, field_name)
                if value:
                    parts.append(value.display_name)
            record.name = " / ".join(parts) or _("Section / Coordination Kiiraaye")

    _unique_reference = models.Constraint("UNIQUE(reference)", "La référence de la section doit être unique.")

    @api.model
    def _default_senegal(self):
        return self.env["res.country"].search([("code", "=", "SN")], limit=1).id

    def _geography_visibility(self):
        return {
            "communale": {"region": True, "departement": True, "commune": True, "quartier": True},
            "departementale": {"region": True, "departement": True, "commune": False, "quartier": False},
            "regionale": {"region": True, "departement": False, "commune": False, "quartier": False},
            "nationale": {"region": False, "departement": False, "commune": False, "quartier": False},
            "diaspora": {"region": False, "departement": False, "commune": False, "quartier": False},
        }

    @api.onchange("country_id", "type_section")
    def _onchange_country_and_type(self):
        mapping = self._geography_visibility()
        visible = mapping.get(self.type_section, {})
        if not self.country_id:
            self.region_id = False; self.departement_id = False; self.commune_id = False; self.quartier_id = False
            return {"domain": {"region_id": [("id", "=", False)], "departement_id": [("id", "=", False)], "commune_id": [("id", "=", False)], "quartier_id": [("id", "=", False)]}}
        if not visible.get("region"): self.region_id = False
        if not visible.get("departement"): self.departement_id = False
        if not visible.get("commune"): self.commune_id = False
        if not visible.get("quartier"): self.quartier_id = False
        if self.region_id and self.region_id.country_id != self.country_id: self.region_id = False
        if self.departement_id and self.departement_id.country_id != self.country_id: self.departement_id = False
        if self.commune_id and self.commune_id.country_id != self.country_id: self.commune_id = False
        if self.quartier_id and self.quartier_id.country_id != self.country_id: self.quartier_id = False
        return {"domain": {
            "region_id": [("country_id", "=", self.country_id.id), ("niveau", "=", "niveau1"), ("active", "=", True)],
            "departement_id": [("country_id", "=", self.country_id.id), ("niveau", "=", "niveau2"), ("parent_id", "=", self.region_id.id or False), ("active", "=", True)],
            "commune_id": [("country_id", "=", self.country_id.id), ("niveau", "=", "niveau3"), ("parent_id", "=", self.departement_id.id or False), ("active", "=", True)],
            "quartier_id": [("country_id", "=", self.country_id.id), ("niveau", "=", "niveau5"), ("parent_id", "child_of", self.commune_id.id) if self.commune_id else ("id", "=", False), ("active", "=", True)],
        }}

    @api.onchange("region_id")
    def _onchange_region_id(self):
        if self.departement_id and self.departement_id.parent_id != self.region_id: self.departement_id = False; self.commune_id = False; self.quartier_id = False
        elif not self.region_id: self.departement_id = False; self.commune_id = False; self.quartier_id = False
        return {"domain": {"departement_id": [("country_id", "=", self.country_id.id), ("niveau", "=", "niveau2"), ("parent_id", "=", self.region_id.id or False), ("active", "=", True)]}}

    @api.onchange("departement_id")
    def _onchange_departement_id(self):
        if self.commune_id and self.commune_id.parent_id != self.departement_id: self.commune_id = False; self.quartier_id = False
        elif not self.departement_id: self.commune_id = False; self.quartier_id = False
        return {"domain": {"commune_id": [("country_id", "=", self.country_id.id), ("niveau", "=", "niveau3"), ("parent_id", "=", self.departement_id.id or False), ("active", "=", True)]}}

    @api.onchange("commune_id")
    def _onchange_commune_id(self):
        if self.quartier_id and self.quartier_id.parent_id and self.commune_id:
            current = self.quartier_id; ancestors = current; valid = False
            while ancestors:
                if ancestors.parent_id == self.commune_id: valid = True; break
                ancestors = ancestors.parent_id
            if not valid: self.quartier_id = False
        elif not self.commune_id: self.quartier_id = False
        return {"domain": {"quartier_id": ([("country_id", "=", self.country_id.id), ("niveau", "=", "niveau5"), ("parent_id", "child_of", self.commune_id.id), ("active", "=", True)] if self.commune_id else [("id", "=", False)])}}

    @api.constrains("country_id", "type_section", "region_id", "departement_id", "commune_id", "quartier_id")
    def _check_geography(self):
        for record in self:
            if record.region_id and (record.region_id.country_id != record.country_id or record.region_id.niveau != "niveau1"):
                raise ValidationError(_("La région doit appartenir au pays sélectionné et être de niveau Région."))
            if record.departement_id and (record.departement_id.country_id != record.country_id or record.departement_id.niveau != "niveau2" or (record.region_id and record.departement_id.parent_id != record.region_id)):
                raise ValidationError(_("Le département doit appartenir à la région et au pays sélectionnés."))
            if record.commune_id and (record.commune_id.country_id != record.country_id or record.commune_id.niveau != "niveau3" or (record.departement_id and record.commune_id.parent_id != record.departement_id)):
                raise ValidationError(_("La commune doit appartenir au département et au pays sélectionnés."))
            if record.quartier_id:
                if record.quartier_id.country_id != record.country_id or record.quartier_id.niveau != "niveau5": raise ValidationError(_("Le quartier doit appartenir au pays sélectionné et être de niveau Quartier."))
                if record.commune_id:
                    current = record.quartier_id.parent_id; valid = False
                    while current:
                        if current == record.commune_id: valid = True; break
                        current = current.parent_id
                    if not valid: raise ValidationError(_("Le quartier doit appartenir à la commune sélectionnée."))
            if record.type_section == "regionale" and not record.region_id: raise ValidationError(_("Une coordination régionale doit avoir une région."))
            if record.type_section == "departementale" and (not record.region_id or not record.departement_id): raise ValidationError(_("Une coordination départementale doit avoir une région et un département."))
            if record.type_section == "communale" and (not record.region_id or not record.departement_id or not record.commune_id or not record.quartier_id): raise ValidationError(_("Une section communale doit avoir une région, un département, une commune et un quartier."))

    @api.constrains("type_section", "country_id", "region_id", "departement_id", "commune_id", "quartier_id")
    def _check_unique_geography_scope(self):
        for record in self:
            if not record.id: continue
            domain = [("id", "!=", record.id), ("type_section", "=", record.type_section), ("country_id", "=", record.country_id.id)]
            if record.type_section == "regionale": domain += [("region_id", "=", record.region_id.id)]
            elif record.type_section == "departementale": domain += [("region_id", "=", record.region_id.id), ("departement_id", "=", record.departement_id.id)]
            elif record.type_section == "communale": domain += [("region_id", "=", record.region_id.id), ("departement_id", "=", record.departement_id.id), ("commune_id", "=", record.commune_id.id), ("quartier_id", "=", record.quartier_id.id)]
            elif record.type_section in ("nationale", "diaspora"): domain += [("region_id", "=", False), ("departement_id", "=", False), ("commune_id", "=", False), ("quartier_id", "=", False)]
            duplicate = self.env["kiiraaye.section"].search(domain, limit=1)
            if duplicate: raise ValidationError(_("Une section/coordination de ce type existe déjà pour cette localisation géographique."))

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get("type_section") in ("nationale", "diaspora"):
                vals.update({"region_id": False, "departement_id": False, "commune_id": False, "quartier_id": False})
        return super().create(vals_list)

    def action_view_hierarchy(self):
        self.ensure_one()
        action = self.env.ref("kiiraaye_governance.action_kiiraaye_section_org_chart").read()[0]
        action["res_id"] = self.id
        action["context"] = dict(self.env.context, active_id=self.id, active_ids=[self.id], active_model="kiiraaye.section")
        return action

    def _section_hierarchy_parent(self):
        self.ensure_one(); Section = self.env["kiiraaye.section"]
        if self.type_section == "regionale": return Section.search([("type_section", "=", "nationale"), ("country_id", "=", self.country_id.id), ("active", "=", True)], order="id", limit=1)
        if self.type_section == "departementale": return Section.search([("type_section", "=", "regionale"), ("country_id", "=", self.country_id.id), ("region_id", "=", self.region_id.id), ("active", "=", True)], order="id", limit=1)
        if self.type_section == "communale": return Section.search([("type_section", "=", "departementale"), ("country_id", "=", self.country_id.id), ("region_id", "=", self.region_id.id), ("departement_id", "=", self.departement_id.id), ("active", "=", True)], order="id", limit=1)
        return Section.browse()

    def _section_hierarchy_children(self):
        self.ensure_one(); Section = self.env["kiiraaye.section"]
        domain = [("active", "=", True), ("country_id", "=", self.country_id.id)]
        if self.type_section == "nationale": domain.append(("type_section", "=", "regionale"))
        elif self.type_section == "regionale": domain += [("type_section", "=", "departementale"), ("region_id", "=", self.region_id.id)]
        elif self.type_section == "departementale": domain += [("type_section", "=", "communale"), ("region_id", "=", self.region_id.id), ("departement_id", "=", self.departement_id.id)]
        else: return Section.browse()
        return Section.search(domain, order="name, id")

    def action_open_siege(self):
        self.ensure_one()
        if not self.siege_partner_id:
            partner = self.env["res.partner"].create({"name": f"Siège - {self.name}", "type": "other", "country_id": self.country_id.id})
            self.siege_partner_id = partner
        return {"type": "ir.actions.act_window", "name": _("Adresse du siège"), "res_model": "res.partner", "res_id": self.siege_partner_id.id, "view_mode": "form", "target": "current"}


class KiiraayeBureauLigne(models.Model):
    _name = "kiiraaye.bureau.ligne"
    _description = "Membre du bureau d'une section ou coordination"
    _rec_name = "name"
    _order = "sequence, id"

    section_id = fields.Many2one("kiiraaye.section", string="(Section/Coordination)", required=True, ondelete="cascade")
    position_id = fields.Many2one("kiiraaye.position", string="Poste", required=True, ondelete="restrict")
    partisan_id = fields.Many2one("kiiraaye.partisan", string="Membre", required=True, ondelete="restrict")
    date_debut = fields.Date(string="Date de début")
    date_fin = fields.Date(string="Date de fin")
    sequence = fields.Integer(string="Séquence", default=10)
    active = fields.Boolean(string="Actif", default=True)
    name = fields.Char(string="Libellé", compute="_compute_name", store=True)
    _dates_check = models.Constraint("CHECK(date_fin IS NULL OR date_debut IS NULL OR date_fin >= date_debut)", "La date de fin ne peut pas être antérieure à la date de début.")

    @api.depends("position_id.name", "partisan_id.nom_complet")
    def _compute_name(self):
        for record in self:
            record.name = " — ".join(value for value in (record.position_id.name, record.partisan_id.nom_complet) if value)

    @api.constrains("section_id", "position_id", "active")
    def _check_active_unique_position(self):
        for record in self.filtered("active"):
            duplicate = self.env["kiiraaye.bureau.ligne"].search([("id", "!=", record.id), ("section_id", "=", record.section_id.id), ("position_id", "=", record.position_id.id), ("active", "=", True)], limit=1)
            if duplicate: raise ValidationError(_("Le poste « %s » ne peut avoir qu'un titulaire actif dans cette section/coordination.") % record.position_id.name)

    @api.constrains("section_id", "partisan_id")
    def _check_member_of_section(self):
        for record in self:
            if record.section_id and record.partisan_id not in record.section_id.membre_ids:
                raise ValidationError(_("Le titulaire d'un poste du bureau doit être membre de la section/coordination."))
