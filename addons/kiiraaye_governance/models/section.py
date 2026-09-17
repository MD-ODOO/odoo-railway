from odoo import api, fields, models, _
from odoo.exceptions import ValidationError


class KiiraayeSection(models.Model):
    _name = "kiiraaye.section"
    _description = "Section / Coordination Kiiraaye"
    _rec_name = "name"
    _order = "name, id"

    name = fields.Char(string="Nom", required=True)
    reference = fields.Char(
        string="Référence",
        required=True,
        copy=False,
        readonly=True,
        default=lambda self: self.env["ir.sequence"].next_by_code("kiiraaye.section") or "Nouveau",
    )
    type_section = fields.Selection(
        [
            ("communale", "Section communale"),
            ("departementale", "Coordination départementale"),
            ("regionale", "Coordination régionale"),
            ("nationale", "Coordination nationale"),
            ("diaspora", "Coordination diaspora"),
        ],
        string="Type de section / coordination",
        required=True,
    )
    country_id = fields.Many2one(
        "res.country",
        string="Pays",
        required=True,
        default=lambda self: self._default_senegal(),
        ondelete="restrict",
    )
    lieu_id = fields.Many2one(
        "kiiraaye.geographie",
        string="Lieu / Zone",
        required=True,
        ondelete="restrict",
    )
    lieu_niveau_attendu = fields.Selection(
        [
            ("pays", "Pays"),
            ("niveau1", "Région / État / Province"),
            ("niveau2", "Département / District / Comté"),
            ("niveau3", "Commune / Municipalité / Ville"),
        ],
        string="Niveau attendu",
        compute="_compute_lieu_niveau_attendu",
        store=True,
    )
    siege_partner_id = fields.Many2one(
        "res.partner",
        string="Siège / Adresse",
        ondelete="restrict",
        copy=False,
        context={"default_type": "other"},
        help="Adresse du siège gérée avec le formulaire d'adresse natif d'Odoo.",
    )
    date_creation = fields.Date(
        string="Date de création",
        default=fields.Date.context_today,
    )
    state = fields.Selection(
        [
            ("ouverte", "Ouverte"),
            ("fermee", "Fermée"),
        ],
        string="État",
        required=True,
        default="ouverte",
    )
    active = fields.Boolean(string="Actif", default=True)
    membre_ids = fields.Many2many(
        "kiiraaye.partisan",
        "kiiraaye_section_partisan_rel",
        "section_id",
        "partisan_id",
        string="Membres",
    )
    bureau_ligne_ids = fields.One2many(
        "kiiraaye.bureau.ligne",
        "section_id",
        string="Membres du bureau",
        copy=True,
    )

    _unique_section_scope = models.Constraint(
        "UNIQUE(type_section, country_id, lieu_id)",
        "Une seule section/coordination de ce type peut être définie pour cette zone et ce pays.",
    )
    _unique_reference = models.Constraint(
        "UNIQUE(reference)",
        "La référence de la section doit être unique.",
    )

    @api.model
    def _default_senegal(self):
        return self.env["res.country"].search([("code", "=", "SN")], limit=1).id

    def _expected_niveau(self):
        return {
            "communale": "niveau3",
            "departementale": "niveau2",
            "regionale": "niveau1",
            "nationale": "pays",
            "diaspora": "pays",
        }

    @api.depends("type_section")
    def _compute_lieu_niveau_attendu(self):
        mapping = self._expected_niveau()
        for record in self:
            record.lieu_niveau_attendu = mapping.get(record.type_section)

    @api.onchange("country_id", "type_section")
    def _onchange_country_and_type(self):
        mapping = self._expected_niveau()
        expected = mapping.get(self.type_section)
        if not self.country_id or not expected:
            self.lieu_id = False
            return

        domain = [
            ("country_id", "=", self.country_id.id),
            ("niveau", "=", expected),
            ("active", "=", True),
        ]
        candidates = self.env["kiiraaye.geographie"].search(domain, limit=1)
        if self.type_section in ("nationale", "diaspora"):
            self.lieu_id = candidates
        elif self.lieu_id and (
            self.lieu_id.country_id != self.country_id
            or self.lieu_id.niveau != expected
        ):
            self.lieu_id = False
        return {"domain": {"lieu_id": domain}}

    @api.model_create_multi
    def create(self, vals_list):
        Geo = self.env["kiiraaye.geographie"]
        for vals in vals_list:
            type_section = vals.get("type_section")
            country_id = vals.get("country_id")
            if type_section in ("nationale", "diaspora") and country_id and not vals.get("lieu_id"):
                root = Geo.search(
                    [("country_id", "=", country_id), ("niveau", "=", "pays")],
                    limit=1,
                )
                if root:
                    vals["lieu_id"] = root.id
        return super().create(vals_list)

    @api.constrains("lieu_id", "country_id", "type_section")
    def _check_lieu(self):
        mapping = self._expected_niveau()
        for record in self:
            if not record.lieu_id:
                continue
            if record.lieu_id.country_id != record.country_id:
                raise ValidationError(_("Le lieu doit appartenir au pays sélectionné."))
            expected = mapping.get(record.type_section)
            if expected and record.lieu_id.niveau != expected:
                raise ValidationError(
                    _("Le niveau du lieu ne correspond pas au type de section ou coordination.")
                )

    @api.constrains("siege_partner_id", "country_id")
    def _check_siege_country(self):
        for record in self:
            if record.siege_partner_id and record.siege_partner_id.country_id:
                if record.siege_partner_id.country_id != record.country_id:
                    raise ValidationError(
                        _("Le pays de l'adresse du siège doit correspondre au pays de la section ou coordination.")
                    )

    def action_open_siege(self):
        self.ensure_one()
        if not self.siege_partner_id:
            partner = self.env["res.partner"].create(
                {
                    "name": f"Siège - {self.name}",
                    "type": "other",
                    "country_id": self.country_id.id,
                }
            )
            self.siege_partner_id = partner
        return {
            "type": "ir.actions.act_window",
            "name": _("Adresse du siège"),
            "res_model": "res.partner",
            "res_id": self.siege_partner_id.id,
            "view_mode": "form",
            "target": "current",
        }


class KiiraayeBureauLigne(models.Model):
    _name = "kiiraaye.bureau.ligne"
    _description = "Membre du bureau d'une section ou coordination"
    _rec_name = "name"
    _order = "sequence, id"

    section_id = fields.Many2one(
        "kiiraaye.section",
        string="Section / Coordination",
        required=True,
        ondelete="cascade",
    )
    position_id = fields.Many2one(
        "kiiraaye.position",
        string="Poste",
        required=True,
        ondelete="restrict",
    )
    partisan_id = fields.Many2one(
        "kiiraaye.partisan",
        string="Membre",
        required=True,
        ondelete="restrict",
    )
    date_debut = fields.Date(string="Date de début")
    date_fin = fields.Date(string="Date de fin")
    sequence = fields.Integer(string="Séquence", default=10)
    active = fields.Boolean(string="Actif", default=True)
    name = fields.Char(
        string="Libellé",
        compute="_compute_name",
        store=True,
    )

    _dates_check = models.Constraint(
        "CHECK(date_fin IS NULL OR date_debut IS NULL OR date_fin >= date_debut)",
        "La date de fin ne peut pas être antérieure à la date de début.",
    )

    @api.depends("position_id.name", "partisan_id.nom_complet")
    def _compute_name(self):
        for record in self:
            record.name = " — ".join(
                value for value in (record.position_id.name, record.partisan_id.nom_complet) if value
            )

    @api.constrains("section_id", "position_id", "active")
    def _check_active_unique_position(self):
        for record in self.filtered("active"):
            duplicate = self.env["kiiraaye.bureau.ligne"].search(
                [
                    ("id", "!=", record.id),
                    ("section_id", "=", record.section_id.id),
                    ("position_id", "=", record.position_id.id),
                    ("active", "=", True),
                ],
                limit=1,
            )
            if duplicate:
                raise ValidationError(
                    _("Le poste « %s » ne peut avoir qu'un titulaire actif dans cette section/coordination.")
                    % record.position_id.name
                )

    @api.constrains("section_id", "partisan_id")
    def _check_member_of_section(self):
        for record in self:
            if record.section_id and record.partisan_id not in record.section_id.membre_ids:
                raise ValidationError(
                    _("Le titulaire d'un poste du bureau doit être membre de la section/coordination.")
                )
