from odoo import fields, models

class KiiraayeNationalReportWizard(models.TransientModel):
    _name = 'kiiraaye.national.report.wizard'
    _description = 'Assistant rapport de gouvernance'

    date_debut = fields.Date(required=True)
    date_fin = fields.Date(required=True)
    territoire_id = fields.Many2one('kiiraaye.territoire')
    report_title = fields.Char(default='Rapport de gouvernance Kiiraaye')

    def action_print(self):
        self.ensure_one()
        return self.env.ref('kiiraaye_governance.action_report_governance').report_action(self)
