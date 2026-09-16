from odoo import api, fields, models, _
from odoo.exceptions import ValidationError


class KiiraayeElection(models.Model):
    _name = "kiiraaye.election"
    _description = "Élection interne Kiiraaye"
    _inherit = ["mail.thread", "mail.activity.mixin"]
    _order = "date desc, id desc"

    name = fields.Char(string="Intitulé", required=True, tracking=True)
    geographie_id = fields.Many2one(
        "kiiraaye.geographie", string="Zone géographique", required=True,
        ondelete="restrict", index=True, tracking=True
    )
    date = fields.Date(
        string="Date de l'élection", required=True,
        default=fields.Date.context_today, tracking=True
    )
    election_type = fields.Selection([
        ("creation_bureau", "Création / installation du bureau"),
        ("renouvellement", "Renouvellement"),
        ("remplacement", "Remplacement"),
        ("autre", "Autre"),
    ], string="Type", required=True, default="creation_bureau")
    state = fields.Selection([
        ("draft", "Brouillon"),
        ("validated", "Validée"),
        ("closed", "Clôturée"),
        ("cancelled", "Annulée"),
    ], string="État", default="draft", tracking=True, required=True)
    pv_document_id = fields.Many2one(
        "kiiraaye.document", string="PV / document associé",
        ondelete="set null"
    )
    result_line_ids = fields.One2many(
        "kiiraaye.election.result.line", "election_id",
        string="Résultats"
    )
    notes = fields.Text(string="Observations")

    def action_validate(self):
        self.write({"state": "validated"})

    def action_close(self):
        self.write({"state": "closed"})

    def action_cancel(self):
        self.write({"state": "cancelled"})


class KiiraayeElectionResultLine(models.Model):
    _name = "kiiraaye.election.result.line"
    _description = "Résultat d'élection interne"

    election_id = fields.Many2one(
        "kiiraaye.election", required=True, ondelete="cascade"
    )
    position_id = fields.Many2one(
        "kiiraaye.position", string="Poste", required=True,
        ondelete="restrict"
    )
    partisan_id = fields.Many2one(
        "kiiraaye.partisan", string="Partisan", required=True,
        ondelete="restrict"
    )
    elected = fields.Boolean(string="Élu", default=True)

    @api.constrains("partisan_id", "election_id")
    def _check_partisan_scope(self):
        for rec in self:
            if rec.partisan_id and rec.election_id:
                allowed = self.env["kiiraaye.geographie"].search([
                    ("id", "child_of", rec.election_id.geographie_id.id)
                ])
                if rec.partisan_id.geographie_id not in allowed:
                    raise ValidationError(
                        _("Le partisan sélectionné est hors du périmètre de l'élection.")
                    )
