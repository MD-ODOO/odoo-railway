from odoo import api, fields, models, _
from odoo.exceptions import UserError

class KiiraayeMemberCard(models.Model):
    _name = 'kiiraaye.member.card'
    _description = 'Carte de membre Kiiraaye'
    _inherit = ['mail.thread','mail.activity.mixin']
    _order = 'id desc'

    name = fields.Char(required=True, copy=False, default='Nouvelle carte')
    partisan_id = fields.Many2one('kiiraaye.partisan', required=True, ondelete='restrict')
    territoire_id = fields.Many2one(related='partisan_id.territoire_id', store=True, index=True)
    section_id = fields.Many2one(related='partisan_id.section_id', store=True)
    poste_id = fields.Many2one(related='partisan_id.poste_actuel_id', store=True)
    photo = fields.Image(related='partisan_id.photo', readonly=True)
    date_emission = fields.Date(default=fields.Date.context_today, required=True)
    date_expiration = fields.Date()
    qr_value = fields.Char(compute='_compute_qr', store=True)
    state = fields.Selection([('draft','Brouillon'),('active','Active'),('expired','Expirée'),('cancelled','Annulée')], default='draft')

    @api.depends('partisan_id.matricule')
    def _compute_qr(self):
        for r in self:
            r.qr_value = r.partisan_id.matricule or ''

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name') == 'Nouvelle carte':
                vals['name'] = self.env['ir.sequence'].next_by_code('kiiraaye.member.card') or vals['name']
        return super().create(vals_list)

    def action_activate(self): self.write({'state':'active'})
    def action_expire(self): self.write({'state':'expired'})
    def action_cancel(self): self.write({'state':'cancelled'})
    def action_print(self):
        self.ensure_one()
        if self.state == 'cancelled':
            raise UserError(_('Une carte annulée ne peut pas être imprimée.'))
        return self.env.ref('kiiraaye_governance.action_report_member_card').report_action(self)
