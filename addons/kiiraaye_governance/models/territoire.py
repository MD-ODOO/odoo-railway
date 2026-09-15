from odoo import api, fields, models, _
from odoo.exceptions import ValidationError

LEVEL = {'quartier': 0, 'communaute_rurale': 1, 'commune': 1, 'departement': 2, 'region': 3}

class KiiraayeTerritoire(models.Model):
    _name = 'kiiraaye.territoire'
    _description = 'Territoire Kiiraaye'
    _parent_store = True
    _parent_name = 'parent_id'
    _rec_name = 'complete_name'

    name = fields.Char(required=True, index=True)
    code = fields.Char(required=True, copy=False, index=True)
    type_niveau = fields.Selection([
        ('quartier','Quartier / Section'), ('communaute_rurale','Communauté rurale'),
        ('commune','Commune'), ('departement','Département'), ('region','Région')
    ], required=True, index=True)
    parent_id = fields.Many2one('kiiraaye.territoire', ondelete='restrict', index=True)
    parent_path = fields.Char(index=True)
    child_ids = fields.One2many('kiiraaye.territoire','parent_id')
    complete_name = fields.Char(compute='_compute_complete_name', store=True)
    active = fields.Boolean(default=True)
    date_creation = fields.Date(default=fields.Date.context_today)
    date_fermeture = fields.Date()
    bureau_id = fields.Many2one('kiiraaye.bureau')
    responsable_ids = fields.Many2many('res.users','kiiraaye_territoire_user_rel','territoire_id','user_id')
    latitude = fields.Float(digits=(10,6))
    longitude = fields.Float(digits=(10,6))
    geojson = fields.Text(help='Géométrie GeoJSON facultative pour intégration cartographique.')
    population_reference = fields.Integer(help='Population de référence agrégée, si disponible.')
    partisan_count = fields.Integer(compute='_compute_counts')
    section_count = fields.Integer(compute='_compute_counts')

    _sql_constraints = [('code_unique','unique(code)','Le code du territoire doit être unique.')]

    @api.depends('name','parent_id.complete_name')
    def _compute_complete_name(self):
        for r in self:
            r.complete_name = f'{r.parent_id.complete_name} / {r.name}' if r.parent_id else r.name

    def _compute_counts(self):
        P, S = self.env['kiiraaye.partisan'], self.env['kiiraaye.section']
        for r in self:
            r.partisan_count = P.search_count([('territoire_id','child_of',r.id)])
            r.section_count = S.search_count([('territoire_id','child_of',r.id)])

    @api.constrains('type_niveau','parent_id')
    def _check_hierarchy(self):
        for r in self:
            if not r.parent_id:
                if r.type_niveau != 'region':
                    raise ValidationError(_('Un territoire racine doit être une région.'))
            elif LEVEL[r.type_niveau] != LEVEL[r.parent_id.type_niveau] - 1:
                raise ValidationError(_('La hiérarchie territoriale est invalide.'))
