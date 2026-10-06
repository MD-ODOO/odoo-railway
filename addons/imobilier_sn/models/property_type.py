# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
from odoo.exceptions import ValidationError


class ImobilierSNPropertyType(models.Model):
    _name = "imobilier.sn.property.type"
    _description = "Type configurable Immobilier SN"
    _order = "category, sequence, name"

    name = fields.Char(string="Nom", required=True, translate=True)
    code = fields.Char(string="Code", required=True, index=True)
    category = fields.Selection(
        [
            ("apartment", "Type d'appartement"),
            ("house", "Type de maison"),
            ("paper", "Type de papier"),
        ],
        string="Catégorie",
        required=True,
        index=True,
    )
    sequence = fields.Integer(string="Séquence", default=10)
    active = fields.Boolean(string="Actif", default=True)

    _name_unique = models.Constraint(
        "UNIQUE(category, name)",
        "Ce nom existe déjà dans cette catégorie.",
    )
    _code_unique = models.Constraint(
        "UNIQUE(category, code)",
        "Ce code existe déjà dans cette catégorie.",
    )

    @api.constrains("name", "code", "category")
    def _check_values(self):
        for rec in self:
            if not rec.name.strip():
                raise ValidationError(_("Le nom ne peut pas être vide."))
            if not rec.code.strip():
                raise ValidationError(_("Le code ne peut pas être vide."))
