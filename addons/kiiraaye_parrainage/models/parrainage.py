from odoo import api, fields, models, _
from odoo.exceptions import ValidationError

class KiiraayeParrainage(models.Model):
    _name = "kiiraaye.parrainage"
    _description = "Parrainage électoral"
    _inherit = ["mail.thread", "mail.activity.mixin"]
    _order = "id desc"
    _rec_name = "name"

    name = fields.Char(string="Référence", required=True, default=lambda self: _("Nouveau"), copy=False, index=True)
    election_id = fields.Many2one("kiiraaye.parrainage.election", string="Élection", required=True, ondelete="restrict")
    scope = fields.Selection([("national","National"),("diaspora","Diaspora")], string="Liste", required=True, default="national", index=True)
    order_number = fields.Integer(string="N° d'ordre", required=True, index=True)
    full_name = fields.Char(string="Prénom(s) et nom", required=True)
    voter_card_number = fields.Char(string="N° carte d'électeur", size=9, index=True)
    nin = fields.Char(string="N.I.N", required=True, index=True)
    cni_expiry_date = fields.Date(string="Expiration CNI")
    birth_date = fields.Date(string="Date de naissance")
    signature = fields.Boolean(string="Signature reçue")
    collection_date = fields.Date(string="Date de collecte", default=fields.Date.context_today)
    collector_name = fields.Char(string="Collecteur")
    collector_voter_card = fields.Char(string="Carte d'électeur du collecteur", size=9)
    country_id = fields.Many2one("res.country", string="Pays", ondelete="restrict")
    region_id = fields.Many2one("kiiraaye.geographie", string="Région", ondelete="restrict", index=True)
    departement_id = fields.Many2one("kiiraaye.geographie", string="Département", ondelete="restrict", index=True)
    commune_id = fields.Many2one("kiiraaye.geographie", string="Commune", ondelete="restrict", index=True)
    quartier_id = fields.Many2one("kiiraaye.geographie", string="Quartier", ondelete="restrict", index=True)
    age = fields.Integer(string="Âge", compute="_compute_age", store=True)
    age_valid = fields.Boolean(string="Âge >= 18", compute="_compute_age", store=True)
    birth_control_status = fields.Selection([("pending","Date à contrôler"),("valid","Valide"),("invalid","Moins de 18 ans")], string="Contrôle âge", compute="_compute_age", store=True)
    active = fields.Boolean(default=True)
    imported = fields.Boolean(string="Importé depuis Excel", default=False, readonly=True)
    source_file = fields.Char(string="Fichier source", readonly=True)

    _sql_nin_election = models.Constraint("UNIQUE(election_id, nin)", "Un même N.I.N ne peut parrainer qu'une seule fois pour une même élection.")

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get("name") in (False, _("Nouveau"), "Nouveau"):
                vals["name"] = self.env["ir.sequence"].next_by_code("kiiraaye.parrainage") or _("Nouveau")
        return super().create(vals_list)

    @api.depends("birth_date")
    def _compute_age(self):
        today = fields.Date.context_today(self)
        for rec in self:
            if not rec.birth_date:
                rec.age, rec.age_valid, rec.birth_control_status = 0, False, "pending"
                continue
            years = today.year - rec.birth_date.year - ((today.month, today.day) < (rec.birth_date.month, rec.birth_date.day))
            rec.age, rec.age_valid = years, years >= 18
            rec.birth_control_status = "valid" if years >= 18 else "invalid"

    @api.constrains("birth_date")
    def _check_birth_date(self):
        today = fields.Date.context_today(self)
        for rec in self:
            if rec.birth_date and rec.birth_date > today:
                raise ValidationError(_("La date de naissance ne peut pas être dans le futur."))
            if rec.birth_date:
                eighteenth = today.replace(year=today.year - 18)
                if rec.birth_date > eighteenth:
                    raise ValidationError(_("Le parrain doit avoir au moins 18 ans."))

    @api.constrains("voter_card_number")
    def _check_voter_card(self):
        for rec in self:
            if rec.voter_card_number and len(rec.voter_card_number) != 9:
                raise ValidationError(_("Le numéro de carte d'électeur doit comporter exactement 9 caractères."))

    @api.constrains("scope", "country_id", "region_id", "commune_id")
    def _check_scope(self):
        for rec in self:
            if rec.scope == "diaspora" and not rec.country_id:
                raise ValidationError(_("Le pays est obligatoire pour un parrainage diaspora."))
            if rec.scope == "national" and (not rec.region_id or not rec.commune_id):
                raise ValidationError(_("La région et la commune sont obligatoires pour un parrainage national."))
            if rec.scope == "national" and rec.country_id and rec.country_id.code != "SN":
                raise ValidationError(_("Un parrainage national doit être rattaché au Sénégal."))

class KiiraayeParrainageElection(models.Model):
    _name = "kiiraaye.parrainage.election"
    _description = "Campagne de parrainage"
    _order = "date_start desc, id desc"

    name = fields.Char(required=True)
    candidate_name = fields.Char(string="Candidat / Liste")
    candidate_number = fields.Char(string="Numéro attribué")
    election_type = fields.Selection([("presidential","Présidentielle"),("legislative","Législative"),("other","Autre")], string="Type d'élection", default="presidential", required=True)
    date_start = fields.Date(string="Début collecte")
    date_end = fields.Date(string="Fin collecte")
    active = fields.Boolean(default=True)
    parrainage_ids = fields.One2many("kiiraaye.parrainage", "election_id", string="Parrainages")
    national_count = fields.Integer(compute="_compute_counts")
    diaspora_count = fields.Integer(compute="_compute_counts")

    def _compute_counts(self):
        for rec in self:
            rec.national_count = self.env["kiiraaye.parrainage"].search_count([("election_id","=",rec.id),("scope","=","national")])
            rec.diaspora_count = self.env["kiiraaye.parrainage"].search_count([("election_id","=",rec.id),("scope","=","diaspora")])
