from odoo import fields, models


class KiiraayeFormation(models.Model):
    _name = "kiiraaye.formation"
    _description = "Formation Kiiraaye"
    _inherit = ["mail.thread", "mail.activity.mixin"]
    _order = "date_debut desc"

    name = fields.Char(string="Formation", required=True)
    territoire_id = fields.Many2one(
        "kiiraaye.territoire", string="Territoire",
        required=True, ondelete="restrict", index=True
    )
    formateur = fields.Char(string="Formateur")
    date_debut = fields.Date(string="Date de début", required=True)
    date_fin = fields.Date(string="Date de fin")
    duree_heures = fields.Float(string="Durée (heures)")
    participant_ids = fields.Many2many(
        "kiiraaye.partisan", "kiiraaye_formation_partisan_rel",
        "formation_id", "partisan_id", string="Participants"
    )
    theme = fields.Text(string="Thème / programme")
    document_id = fields.Many2one(
        "kiiraaye.document", string="Support / attestation",
        ondelete="set null"
    )
    state = fields.Selection([
        ("draft", "Brouillon"),
        ("planned", "Planifiée"),
        ("done", "Terminée"),
        ("cancelled", "Annulée"),
    ], default="draft", tracking=True)

    def action_plan(self):
        self.write({"state": "planned"})

    def action_done(self):
        self.write({"state": "done"})

    def action_cancel(self):
        self.write({"state": "cancelled"})
