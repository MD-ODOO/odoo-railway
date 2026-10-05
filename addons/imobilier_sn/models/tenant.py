from odoo import fields, models


class ImobilierSNTenantProfile(models.Model):
    _name = "imobilier.sn.tenant.profile"
    _description = "Dossier locataire"
    _rec_name = "partner_id"

    partner_id = fields.Many2one(
        "res.partner",
        string="Locataire",
        required=True,
        ondelete="cascade",
    )
    social_situation = fields.Char(string="Situation sociale")
    profession = fields.Char(string="Profession")
    source_income = fields.Char(string="Source de revenu")
    salary_bulletin = fields.Binary(string="Bulletin de salaire")
    salary_bulletin_filename = fields.Char(string="Nom du fichier")
    other_income_document = fields.Binary(string="Justificatif autre revenu")
    other_income_document_filename = fields.Char(string="Nom du justificatif")
    notes = fields.Text(string="Observations")
