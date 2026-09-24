# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
from odoo.exceptions import ValidationError


class SenegalSalaryCategory(models.Model):
    _name = 'paie.senegal.salary.category'
    _description = 'Catégorie socio-professionnelle'
    _order = 'sequence, code, id'

    name = fields.Char(
        string='Libellé',
        required=True,
    )
    code = fields.Char(
        string='Code',
        required=True,
    )
    base_salary = fields.Monetary(
        string='Salaire de base',
        currency_field='currency_id',
        required=True,
        default=0.0,
    )
    hourly_salary = fields.Float(
        string='Salaire horaire',
        digits=(16, 3),
        help='Salaire horaire prévu par le barème de la Convention collective du Commerce.',
    )
    revaluation_rate = fields.Float(
        string='Taux de revalorisation',
        digits=(16, 2),
        help='Taux de revalorisation appliqué au barème de juillet 2023.',
    )
    sequence = fields.Integer(
        string='Séquence',
        default=10,
    )
    active = fields.Boolean(
        string='Actif',
        default=True,
    )
    currency_id = fields.Many2one(
        'res.currency',
        string='Devise',
        default=lambda self: self.env.company.currency_id,
        required=True,
        readonly=True,
    )
    note = fields.Text(
        string='Observation',
    )

    _sql_constraints = [
        (
            'code_unique',
            'unique(code)',
            _('Le code de la catégorie doit être unique.'),
        ),
    ]

    @api.constrains('base_salary')
    def _check_base_salary(self):
        for record in self:
            if record.base_salary < 0:
                raise ValidationError(
                    _('Le salaire de base ne peut pas être négatif.')
                )
