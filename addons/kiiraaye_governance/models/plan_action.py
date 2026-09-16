from odoo import api, fields, models, _


class KiiraayePlanAction(models.Model):
    _name = "kiiraaye.plan.action"
    _description = "Plan d'action géographique"
    _inherit = ["mail.thread", "mail.activity.mixin"]
    _order = "priority desc, date_fin, id"

    name = fields.Char(string="Action", required=True, tracking=True)
    geographie_id = fields.Many2one(
        "kiiraaye.geographie", string="Zone géographique",
        required=True, ondelete="restrict", index=True
    )
    responsible_id = fields.Many2one(
        "res.users", string="Responsable", tracking=True
    )
    date_debut = fields.Date(
        string="Date de début", default=fields.Date.context_today
    )
    date_fin = fields.Date(string="Échéance")
    priority = fields.Selection([
        ("0", "Normal"),
        ("1", "Important"),
        ("2", "Urgent"),
    ], default="0", string="Priorité")
    state = fields.Selection([
        ("draft", "Brouillon"),
        ("in_progress", "En cours"),
        ("done", "Terminé"),
        ("cancelled", "Annulé"),
    ], default="draft", tracking=True)
    constat = fields.Text(string="Constat")
    action_description = fields.Text(string="Action")
    indicator = fields.Char(string="Indicateur de suivi")
    result = fields.Text(string="Résultat")

    def action_start(self):
        self.write({"state": "in_progress"})

    def action_done(self):
        self.write({"state": "done"})

    def action_cancel(self):
        self.write({"state": "cancelled"})
