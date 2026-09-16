from odoo import api, fields, models, _
from odoo.exceptions import ValidationError


class KiiraayeDocument(models.Model):
    _name = "kiiraaye.document"
    _description = "Document Kiiraaye"
    _inherit = ["mail.thread", "mail.activity.mixin"]
    _order = "date_document desc, id desc"

    name = fields.Char(string="Titre", required=True, tracking=True)
    reference = fields.Char(
        string="Référence", required=True, copy=False, index=True
    )
    document_type = fields.Selection([
        ("pv", "PV"),
        ("decision", "Décision"),
        ("nomination", "Nomination"),
        ("revoke", "Révocation"),
        ("meeting", "Réunion"),
        ("report", "Rapport"),
        ("regulation", "Statut / règlement"),
        ("correspondence", "Correspondance"),
        ("other", "Autre"),
    ], string="Type de document", required=True, default="other")
    date_document = fields.Date(
        string="Date du document", default=fields.Date.context_today,
        required=True
    )
    geographie_id = fields.Many2one(
        "kiiraaye.geographie", string="Zone géographique",
        ondelete="restrict", index=True
    )
    partisan_id = fields.Many2one(
        "kiiraaye.partisan", string="Partisan",
        ondelete="set null"
    )
    election_id = fields.Many2one(
        "kiiraaye.election", string="Élection",
        ondelete="set null"
    )
    attachment = fields.Binary(
        string="Fichier", attachment=True, required=True
    )
    attachment_filename = fields.Char(string="Nom du fichier")
    confidential = fields.Boolean(string="Confidentiel")
    active = fields.Boolean(default=True)

    _reference_unique = models.Constraint(
        "UNIQUE(reference)",
        "La référence du document doit être unique."
    )
    @api.constrains("attachment_filename")
    def _check_pdf_name(self):
        for rec in self:
            if rec.document_type == "pv" and rec.attachment_filename:
                if not rec.attachment_filename.lower().endswith(".pdf"):
                    raise ValidationError(
                        _("Un PV doit être fourni au format PDF.")
                    )
