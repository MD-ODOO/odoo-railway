from odoo import fields, models
from odoo.tools.sql import column_exists, create_column


class ResCompany(models.Model):
    _inherit = "res.company"

    appbar_image = fields.Binary(
        string="Apps Menu Footer Image",
        attachment=True,
    )

    appbar_background_color = fields.Char(
        string="AppsBar Background Color",
        default="#172033",
        help="Couleur libre utilisée comme couleur de fond principale de la barre des applications.",
    )

    def _auto_init(self):
        # Répare automatiquement les bases où le champ Python existe déjà
        # mais où la colonne SQL n'a pas encore été créée.
        if not column_exists(self.env.cr, "res_company", "appbar_background_color"):
            create_column(
                self.env.cr,
                "res_company",
                "appbar_background_color",
                "varchar",
            )
        return super()._auto_init()
