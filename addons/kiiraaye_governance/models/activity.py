from odoo import fields, models


class KiiraayeActivity(models.Model):
    _name = "kiiraaye.activite"
    _description = "Activité territoriale"
    _inherit = ["mail.thread", "mail.activity.mixin"]
    _order = "date desc"

    name = fields.Char(string="Activité", required=True)
    territoire_id = fields.Many2one(
        "kiiraaye.territoire", string="Territoire",
        required=True, ondelete="restrict", index=True
    )
    date = fields.Datetime(string="Date", required=True)
    activity_type = fields.Selection([
        ("meeting", "Réunion"),
        ("training", "Formation"),
        ("assembly", "Assemblée"),
        ("administrative", "Activité administrative"),
        ("other", "Autre"),
    ], string="Type", required=True, default="other")
    responsible_id = fields.Many2one(
        "res.users", string="Responsable"
    )
    participant_ids = fields.Many2many(
        "kiiraaye.partisan", "kiiraaye_activity_partisan_rel",
        "activity_id", "partisan_id", string="Participants"
    )
    notes = fields.Text(string="Compte rendu")
    document_id = fields.Many2one(
        "kiiraaye.document", string="Document associé",
        ondelete="set null"
    )
