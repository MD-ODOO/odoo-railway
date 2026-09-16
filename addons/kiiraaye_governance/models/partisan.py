import re
from odoo import api, fields, models, _
from odoo.exceptions import ValidationError

class KiiraayePartisan(models.Model):
    _name = "kiiraaye.partisan"
    _description = "Partisan / membre"
    _inherit = ["mail.thread", "mail.activity.mixin"]
    _order = "nom, prenom"

    name = fields.Char(
        string="Nom complet", compute="_compute_name", store=True, index=True
    )
    matricule = fields.Char(string="Matricule", required=True, copy=False, index=True)
    nom = fields.Char(string="Nom", required=True, tracking=True)
    prenom = fields.Char(string="Prénom", required=True, tracking=True)
    date_naissance = fields.Date(string="Date de naissance", required=True)
    lieu_naissance = fields.Char(string="Lieu de naissance", required=True)
    numero_id_national = fields.Char(
        string="N° ID national", required=True, copy=False, index=True
    )
    photo = fields.Image(string="Photo", max_width=1024, max_height=1024)
    section_id = fields.Many2one(
        "kiiraaye.section", string="Section", required=True,
        ondelete="restrict", tracking=True
    )
    territoire_id = fields.Many2one(
        related="section_id.territoire_id", store=True, index=True
    )
    date_adhesion = fields.Date(
        string="Date d'adhésion", default=fields.Date.context_today
    )
    active = fields.Boolean(default=True)
    poste_ids = fields.One2many(
        "kiiraaye.poste", "partisan_id", string="Historique des postes"
    )
    poste_actuel_id = fields.Many2one(
        "kiiraaye.poste", string="Poste actuel",
        compute="_compute_poste_actuel", store=True
    )

    _sql_constraints = [
        ("matricule_unique", "unique(matricule)",
         "Le matricule doit être unique."),
        ("id_national_unique", "unique(numero_id_national)",
         "Ce numéro d'identification national existe déjà."),
    ]

    @api.depends("nom", "prenom", "matricule")
    def _compute_name(self):
        for rec in self:
            rec.name = f"{rec.nom or ''} {rec.prenom or ''} [{rec.matricule or ''}]".strip()

    @api.depends(
        "poste_ids.state", "poste_ids.date_debut",
        "poste_ids.date_fin", "poste_ids.position_id"
    )
    def _compute_poste_actuel(self):
        today = fields.Date.context_today(self)
        for rec in self:
            actifs = rec.poste_ids.filtered(
                lambda p: p.state == "actif"
                and p.date_debut <= today
                and (not p.date_fin or p.date_fin >= today)
            )
            rec.poste_actuel_id = actifs.sorted(
                key=lambda p: p.date_debut, reverse=True
            )[:1]

    @api.constrains("numero_id_national")
    def _check_id_national(self):
        for rec in self:
            value = rec.numero_id_national or ""
            if not re.fullmatch(r"\d{1,13}", value):
                raise ValidationError(
                    _("Le N° ID national doit contenir uniquement 1 à 13 chiffres.")
                )

    @api.constrains("section_id")
    def _check_section_open(self):
        for rec in self:
            if rec.section_id and rec.section_id.state != "ouverte":
                raise ValidationError(
                    _("Impossible d'inscrire un partisan dans une section fermée.")
                )

    def action_print_member_card(self):
        self.ensure_one()
        Card = self.env["kiiraaye.member.card"]
        card = Card.search(
            [("partisan_id", "=", self.id), ("state", "!=", "cancelled")],
            order="date_emission desc, id desc",
            limit=1,
        )
        if not card:
            card = Card.create({"partisan_id": self.id})
            card.action_activate()
        return card.action_print()
