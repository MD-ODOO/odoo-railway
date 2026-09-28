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

    def get_appsbar_background_color(self):
        """Return the AppsBar color derived from the company's standard Odoo color."""
        self.ensure_one()
        # Même palette que le sélecteur de couleur Odoo 19.
        palette = {
            0: "#A2A2A2",
            1: "#EE2D2D",
            2: "#DC8534",
            3: "#E8BB1D",
            4: "#5794DD",
            5: "#9F628F",
            6: "#DB8865",
            7: "#41A9A2",
            8: "#304BE0",
            9: "#EE2F8A",
            10: "#61C36E",
            11: "#9872E6",
        }
        return palette.get(self.color, self.appbar_background_color or "#172033")

    def _ensure_appbar_background_column(self):
        if not column_exists(self.env.cr, "res_company", "appbar_background_color"):
            create_column(
                self.env.cr,
                "res_company",
                "appbar_background_color",
                "varchar",
            )

    def _auto_init(self):
        # Répare automatiquement les bases où le champ Python existe déjà
        # mais où la colonne SQL n'a pas encore été créée.
        self._ensure_appbar_background_column()
        return super()._auto_init()

    def _register_hook(self):
        # Sécurise aussi les bases existantes au démarrage du registre,
        # avant toute requête HTTP pouvant lire res.company.
        self._ensure_appbar_background_column()
        return super()._register_hook()
