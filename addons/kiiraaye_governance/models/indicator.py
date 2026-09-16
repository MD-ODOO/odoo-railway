from odoo import api, fields, models
class KiiraayeIndicateur(models.Model):
    _name='kiiraaye.indicateur'; _description='Indicateur organisationnel'; _order='score_global desc'
    geographie_id=fields.Many2one('kiiraaye.geographie',required=True,ondelete='cascade',index=True)
    date_calcul=fields.Date(default=fields.Date.context_today,required=True)
    sections_ouvertes=fields.Integer(compute='_calc',store=True); sections_fermees=fields.Integer(compute='_calc',store=True)
    bureaux_complets=fields.Integer(compute='_calc',store=True); bureaux_incomplets=fields.Integer(compute='_calc',store=True)
    membres=fields.Integer(compute='_calc',store=True); activites=fields.Integer(compute='_calc',store=True); formations=fields.Integer(compute='_calc',store=True)
    score_couverture=fields.Float(compute='_scores',store=True); score_activite=fields.Float(compute='_scores',store=True); score_continuite=fields.Float(compute='_scores',store=True); score_global=fields.Float(compute='_scores',store=True)
    niveau=fields.Selection([('critique','Critique'),('renforcer','À renforcer'),('stable','Stable'),('solide','Solide')],compute='_scores',store=True)
    @api.depends('geographie_id')
    def _calc(self):
        for r in self:
            d=[('geographie_id','child_of',r.geographie_id.id)]
            s=self.env['kiiraaye.section'].search(d); b=self.env['kiiraaye.bureau'].search(d)
            r.sections_ouvertes=len(s.filtered(lambda x:x.state=='ouverte')); r.sections_fermees=len(s)-r.sections_ouvertes
            r.bureaux_complets=len(b.filtered(lambda x:len(x.poste_ids.filtered(lambda p:p.state=='actif'))>=5)); r.bureaux_incomplets=len(b)-r.bureaux_complets
            r.membres=self.env['kiiraaye.partisan'].search_count(d+[('active','=',True)])
            r.activites=self.env['kiiraaye.activite'].search_count(d); r.formations=self.env['kiiraaye.formation'].search_count(d)
    @api.depends('sections_ouvertes','sections_fermees','bureaux_complets','bureaux_incomplets','membres','activites','formations')
    def _scores(self):
        for r in self:
            ts=r.sections_ouvertes+r.sections_fermees; tb=r.bureaux_complets+r.bureaux_incomplets
            cs=r.sections_ouvertes/ts*100 if ts else 0; cb=r.bureaux_complets/tb*100 if tb else 0
            r.score_couverture=(cs+cb)/2 if ts or tb else 0
            r.score_activite=min(100, r.activites*4+r.formations*6)
            r.score_continuite=min(100, r.membres)
            r.score_global=.5*r.score_couverture+.3*r.score_activite+.2*r.score_continuite
            r.niveau='critique' if r.score_global<35 else 'renforcer' if r.score_global<55 else 'stable' if r.score_global<75 else 'solide'
