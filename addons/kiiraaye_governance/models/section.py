from odoo import api, fields, models, _
from odoo.exceptions import UserError, ValidationError


class KiiraayeSection(models.Model):
    _name = "kiiraaye.section"
    _description = "Section / Coordination"
    _inherit = ["mail.thread", "mail.activity.mixin"]
    _order = "date_creation desc, name"

    name = fields.Char(string="Nom", required=True, tracking=True)
    reference = fields.Char(
        string="Référence", required=True, copy=False, readonly=True,
        default=lambda self: _("Nouveau")
    )
    date_creation = fields.Date(
        string="Date de création", required=True,
        default=fields.Date.context_today, tracking=True
    )

    type_section = fields.Selection([
        ("communale", "Section communale"),
        ("departementale", "Coordination départementale"),
        ("regionale", "Coordination régionale"),
        ("nationale", "Coordination nationale"),
        ("diaspora", "Coordination diaspora"),
    ], string="Type de section / coordination", required=True, tracking=True)

    lieu_id = fields.Many2one(
        "kiiraaye.geographie", string="Lieu / Zone", required=True,
        ondelete="restrict", index=True,
        help="Le niveau disponible est déterminé automatiquement par le type de section."
    )
    country_id = fields.Many2one(
        related="lieu_id.country_id", store=True, readonly=True, string="Pays"
    )

    # Siège : structure proche de l'adresse standard Odoo.
    siege_street = fields.Char(string="Adresse du siège")
    siege_street2 = fields.Char(string="Complément d'adresse")
    siege_zip = fields.Char(string="Code postal")
    siege_city = fields.Char(string="Ville")
    siege_state_id = fields.Many2one(
        "res.country.state", string="État / Région du siège",
        domain="[('country_id', '=', siege_country_id)]"
    )
    siege_country_id = fields.Many2one(
        "res.country", string="Pays du siège"
    )
    siege_geo_id = fields.Many2one(
        "kiiraaye.geographie", string="Zone géographique du siège",
        domain="[('country_id', '=', siege_country_id)]"
    )

    bureau_id = fields.Many2one(
        "kiiraaye.bureau", string="Bureau",
        readonly=True, copy=False, ondelete="set null"
    )

    membre_ids = fields.Many2many(
        "kiiraaye.partisan", "kiiraaye_section_partisan_rel",
        "section_id", "partisan_id", string="Membres"
    )
    poste_ids = fields.One2many(
        related="bureau_id.poste_ids", string="Membres du bureau / postes", readonly=True
    )

    state = fields.Selection([
        ("ouverte", "Ouverte"),
        ("fermee", "Fermée"),
    ], default="ouverte", required=True, tracking=True)
    date_fermeture = fields.Date(string="Date de fermeture", tracking=True)
    motif_fermeture = fields.Text(string="Motif de fermeture")

    pv_creation = fields.Binary(string="PV de création", attachment=True)
    pv_creation_filename = fields.Char()
    photo = fields.Image(string="Photo")

    _reference_unique = models.Constraint(
        "UNIQUE(reference)",
        "La référence doit être unique."
    )
    @api.onchange("type_section")
    def _onchange_type_section(self):
        for rec in self:
            allowed = rec._get_allowed_levels(rec.type_section)
            domain = [("niveau", "in", allowed)] if allowed else [("id", "=", False)]
            if rec.type_section in ("nationale", "diaspora"):
                senegal = rec._get_default_senegal()
                rec.lieu_id = senegal or False
                return {"domain": {"lieu_id": domain}}
            rec.lieu_id = False
            return {"domain": {"lieu_id": domain}}

    @api.onchange("siege_country_id")
    def _onchange_siege_country(self):
        for rec in self:
            rec.siege_state_id = False
            rec.siege_geo_id = False
            if rec.siege_country_id and rec.siege_country_id.code == "SN":
                # On privilégie le pays sélectionné pour le siège.
                rec.siege_geo_id = rec._get_default_senegal()

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get("reference", _("Nouveau")) == _("Nouveau"):
                vals["reference"] = self.env["ir.sequence"].next_by_code("kiiraaye.section") or _("Nouveau")
            type_section = vals.get("type_section")
            if type_section in ("nationale", "diaspora") and not vals.get("lieu_id"):
                senegal = self._get_default_senegal()
                if senegal:
                    vals["lieu_id"] = senegal.id
        records = super().create(vals_list)
        records._validate_lieux()
        Bureau = self.env["kiiraaye.bureau"]
        for rec in records:
            bureau = Bureau.create({"section_id": rec.id})
            rec.bureau_id = bureau.id
        return records

    def write(self, vals):
        res = super().write(vals)
        if "type_section" in vals or "lieu_id" in vals:
            self._validate_lieux()
        return res

    def _validate_lieux(self):
        for rec in self:
            if not rec.lieu_id:
                raise ValidationError(_("Le lieu/zone est obligatoire."))
            allowed = rec._get_allowed_levels(rec.type_section)
            if rec.lieu_id.niveau not in allowed:
                raise ValidationError(_(
                    "Le lieu sélectionné ne correspond pas au type de section/coordination."
                ))

    @api.constrains("lieu_id", "type_section")
    def _check_lieu(self):
        self._validate_lieux()

    @api.constrains("membre_ids", "state")
    def _check_members(self):
        for rec in self:
            if rec.state == "fermee" and rec.membre_ids:
                # Les membres historiques peuvent rester associés, donc aucune suppression automatique.
                continue

    def action_fermer(self):
        for rec in self:
            if rec.state == "fermee":
                continue
            if not rec.motif_fermeture:
                raise UserError(_("Veuillez renseigner le motif de fermeture."))
            rec.write({
                "state": "fermee",
                "date_fermeture": fields.Date.context_today(self),
            })

    def action_ouvrir(self):
        self.write({"state": "ouverte", "date_fermeture": False})
