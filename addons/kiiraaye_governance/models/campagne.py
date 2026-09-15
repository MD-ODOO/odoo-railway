from odoo import api, fields, models
class KiiraayeCampagne(models.Model):
    _name='kiiraaye.campagne'; _description='Campagne / période historique'
    name=fields.Char(required=True); date_debut=fields.Date(); date_fin=fields.Date(); description=fields.Text(); resultat_ids=fields.One2many('kiiraaye.resultat','campagne_id')
class KiiraayeResultat(models.Model):
    _name='kiiraaye.resultat'; _description='Résultat territorial agrégé'
    campagne_id=fields.Many2one('kiiraaye.campagne',required=True,ondelete='cascade',index=True); territoire_id=fields.Many2one('kiiraaye.territoire',required=True,ondelete='restrict',index=True)
    inscrits=fields.Integer(); votants=fields.Integer(); voix_parti=fields.Integer(); score_pct=fields.Float(compute='_score',store=True); participation_pct=fields.Float(compute='_part',store=True)
    @api.depends('voix_parti','votants')
    def _score(self):
        for r in self:r.score_pct=r.voix_parti/r.votants*100 if r.votants else 0
    @api.depends('votants','inscrits')
    def _part(self):
        for r in self:r.participation_pct=r.votants/r.inscrits*100 if r.inscrits else 0
    _sql_constraints=[('uniq','unique(campagne_id,territoire_id)','Résultat déjà saisi pour cette campagne et ce territoire.')]
