# -*- coding: utf-8 -*-
from odoo import api, fields, models


class ProductTemplate(models.Model):
    _inherit = "product.template"

    imobilier_property_id = fields.Many2one(
        "imobilier.sn.property",
        string="Produit immobilier",
        readonly=True,
        copy=False,
        index=True,
        ondelete="set null",
    )

    _imobilier_property_unique = models.Constraint(
        "UNIQUE(imobilier_property_id)",
        "Un produit catalogue ne peut être lié qu'à un seul produit immobilier.",
    )


class ProductProduct(models.Model):
    _inherit = "product.product"

    imobilier_property_id = fields.Many2one(
        related="product_tmpl_id.imobilier_property_id",
        string="Produit immobilier",
        readonly=True,
        store=True,
    )
