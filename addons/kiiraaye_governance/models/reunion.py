from odoo import fields, models


class KiiraayeReunion(models.Model):
    _name = "kiiraaye.reunion"
    _description = "Réunion Kiiraaye"
    _inherit = ["mail.thread", "mail.activity.mixin"]
    _order = "date_debut desc, id desc"

    name = fields.Char(string="Objet", required=True, tracking=True)
    geographie_id = fields.Many2one(
        "kiiraaye.geographie", string="Zone géographique",
        required=True, ondelete="restrict", index=True
    )
    date_debut = fields.Datetime(string="Début", required=True)
    date_fin = fields.Datetime(string="Fin")
    lieu = fields.Char(string="Lieu")
    reunion_type = fields.Selection([
        ("national", "Nationale"),
        ("regional", "Régionale"),
        ("departemental", "Départementale"),
        ("communal", "Communale"),
        ("coordination", "Coordination"),
        ("section", "Section"),
        ("other", "Autre"),
    ], string="Type", required=True, default="section")
    participant_ids = fields.Many2many(
        "kiiraaye.partisan", "kiiraaye_reunion_partisan_rel",
        "reunion_id", "partisan_id", string="Participants"
    )
    ordre_du_jour = fields.Text(string="Ordre du jour")
    decisions = fields.Text(string="Décisions")
    document_id = fields.Many2one(
        "kiiraaye.document", string="PV / compte rendu",
        ondelete="set null"
    )
    state = fields.Selection([
        ("draft", "Prévue"),
        ("done", "Tenue"),
        ("cancelled", "Annulée"),
    ], default="draft", tracking=True)

    def action_done(self):
        self.write({"state": "done"})

    def action_cancel(self):
        self.write({"state": "cancelled"})
