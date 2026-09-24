# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
from odoo.exceptions import ValidationError

from .salary_engine import (
    TRANSPORT_AMOUNT,
    compute_family_parts,
    solve_gross_for_net,
)


class SenegalSalarySimulation(models.Model):
    _name = 'paie.senegal.salary.simulation'
    _description = 'Simulation de salaire net'
    _order = 'create_date desc, id desc'

    name = fields.Char(
        string='Référence',
        required=True,
        readonly=True,
        copy=False,
        default=lambda self: _('Nouveau'),
    )

    candidate_name = fields.Char(
        string='Employé / Candidat',
        help='Saisie libre, sans liaison avec un employé Odoo.',
    )

    category_id = fields.Many2one(
        'paie.senegal.salary.category',
        string='Catégorie socio-professionnelle',
        required=True,
    )

    status = fields.Selection(
        [
            ('non_cadre', 'Non cadre'),
            ('cadre', 'Cadre'),
        ],
        string='Statut',
        required=True,
        default='non_cadre',
    )

    marital = fields.Selection(
        [
            ('single', 'Célibataire'),
            ('married', 'Marié(e)'),
            ('divorced', 'Divorcé(e)'),
            ('widower', 'Veuf / Veuve'),
        ],
        string='Situation matrimoniale',
        required=True,
        default='single',
    )

    children_count = fields.Integer(
        string='Nombre d’enfants à charge',
        default=0,
    )

    spouse_has_income = fields.Boolean(
        string='Conjoint(e) avec revenu imposable',
        help='Champ neutre, utilisable quel que soit le sexe du salarié ou du conjoint.',
    )

    part_ir = fields.Float(
        string='Parts IR',
        compute='_compute_family_parts',
        store=True,
        digits=(16, 2),
    )

    trimf_persons = fields.Float(
        string='Personnes TRIMF',
        compute='_compute_family_parts',
        store=True,
        digits=(16, 2),
    )

    net_target = fields.Monetary(
        string='Salaire net souhaité',
        currency_field='currency_id',
        required=True,
        default=0.0,
    )

    base_salary = fields.Monetary(
        string='Salaire de base',
        currency_field='currency_id',
        compute='_compute_simulation',
        store=True,
    )

    sursalaire = fields.Monetary(
        string='Sursalaire',
        currency_field='currency_id',
        compute='_compute_simulation',
        store=True,
    )

    ir_amount = fields.Monetary(
        string='IR',
        currency_field='currency_id',
        compute='_compute_simulation',
        store=True,
    )

    trimf_amount = fields.Monetary(
        string='TRIMF',
        currency_field='currency_id',
        compute='_compute_simulation',
        store=True,
    )

    ipres_rg = fields.Monetary(
        string='IPRES RG',
        currency_field='currency_id',
        compute='_compute_simulation',
        store=True,
    )

    ipres_rc = fields.Monetary(
        string='IPRES RC',
        currency_field='currency_id',
        compute='_compute_simulation',
        store=True,
    )

    transport = fields.Monetary(
        string='Transport',
        currency_field='currency_id',
        compute='_compute_simulation',
        store=True,
    )

    net_salary = fields.Monetary(
        string='Salaire net',
        currency_field='currency_id',
        compute='_compute_simulation',
        store=True,
    )

    currency_id = fields.Many2one(
        'res.currency',
        string='Devise',
        default=lambda self: self.env.company.currency_id,
        required=True,
        readonly=True,
    )

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if not vals.get('name') or vals.get('name') == _('Nouveau'):
                vals['name'] = (
                    self.env['ir.sequence'].next_by_code(
                        'paie.senegal.salary.simulation'
                    )
                    or _('Nouveau')
                )

        return super().create(vals_list)

    @api.depends(
        'marital',
        'children_count',
        'spouse_has_income',
    )
    def _compute_family_parts(self):
        for record in self:
            record.part_ir, record.trimf_persons = compute_family_parts(
                record.marital,
                record.children_count,
                record.spouse_has_income,
            )

    @api.constrains(
        'children_count',
        'net_target',
    )
    def _check_inputs(self):
        for record in self:
            if record.children_count < 0:
                raise ValidationError(
                    _('Le nombre d’enfants ne peut pas être négatif.')
                )

            if record.net_target < 0:
                raise ValidationError(
                    _('Le salaire net souhaité ne peut pas être négatif.')
                )

    @api.depends(
        'category_id',
        'category_id.base_salary',
        'status',
        'net_target',
        'part_ir',
        'trimf_persons',
    )
    def _compute_simulation(self):
        for record in self:
            base_salary = (
                record.category_id.base_salary
                if record.category_id
                else 0.0
            )

            result = solve_gross_for_net(
                record.net_target,
                base_salary,
                record.part_ir,
                record.trimf_persons,
                record.status,
            )

            record.base_salary = base_salary
            record.sursalaire = max(
                result['gross'] - base_salary,
                0.0,
            )
            record.ir_amount = result['ir']
            record.trimf_amount = result['trimf']
            record.ipres_rg = result['ipres_rg']
            record.ipres_rc = result['ipres_rc']
            record.transport = TRANSPORT_AMOUNT
            record.net_salary = result['net_salary']

    def action_recompute(self):
        for record in self:
            record._compute_family_parts()
            record._compute_simulation()

        return True
