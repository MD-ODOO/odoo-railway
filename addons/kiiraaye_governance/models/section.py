from odoo import api, fields, models, _
from odoo.exceptions import UserError, ValidationError

class KiiraayeSection(models.Model):
    _name = "kiiraaye.section"
    _description = "Section / quartier"
    _inherit = ["mail.thread", "mail.activity.mixin"]
    _order = "date_creation desc, name"

    name = fields.Char(string="Nom de la section", required=True)
    reference = fields.Char(
        string="Référence", required=True, copy=False, readonly=True,
        default=lambda self: _("Nouveau")
    )
    date_creation = fields.Date(
        string="Date de création", required=True,
        default=fields.Date.context_today, tracking=True
    )
    territoire_id = fields.Many2one(
        "kiiraaye.territoire", string="Quartier",
        required=True, ondelete="restrict",
        domain="[('type_niveau','=','quartier')]"
    )
    commune_id = fields.Many2one(
        "kiiraaye.territoire", string="Commune",
        required=True, ondelete="restrict",
        domain="[('type_niveau','=','commune')]"
    )
    bureau_id = fields.Many2one(
        "kiiraaye.bureau", string="Bureau", ondelete="restrict"
    )
    coordonnateur_id = fields.Many2one(
        "kiiraaye.partisan", related="bureau_id.coordonnateur_id",
        string="Coordonnateur", store=True
    )
    membre_ids = fields.Many2many(
        "kiiraaye.partisan", "kiiraaye_section_partisan_rel",
        "section_id", "partisan_id", string="Membres"
    )
    state = fields.Selection([
        ("ouverte", "Ouverte"),
        ("fermee", "Fermée"),
    ], default="ouverte", required=True, tracking=True)
    date_fermeture = fields.Date(string="Date de fermeture", tracking=True)
    motif_fermeture = fields.Text(string="Motif de fermeture")
    pv_creation = fields.Binary(string="PV de création", attachment=True)
    pv_creation_filename = fields.Char()
    photo = fields.Image(string="Photo")

    _sql_constraints = [
        ("reference_unique", "unique(reference)",
         "La référence de section doit être unique."),
    ]

    @api.onchange("territoire_id")
    def _onchange_territoire(self):
        for rec in self:
            if rec.territoire_id and rec.territoire_id.parent_id:
                parents = rec.territoire_id.parent_id
                commune = parents if parents.type_niveau == "commune" else False
                if not commune:
                    commune = self.env["kiiraaye.territoire"].search([
                        ("id", "parent_of", rec.territoire_id.id),
                        ("type_niveau", "=", "commune"),
                    ], limit=1)
                rec.commune_id = commune

    @api.constrains("territoire_id", "commune_id")
    def _check_territory(self):
        for rec in self:
            if not rec.territoire_id or not rec.commune_id:
                continue
            communes = self.env["kiiraaye.territoire"].search([
                ("id", "parent_of", rec.territoire_id.id),
                ("type_niveau", "=", "commune"),
            ])
            if rec.commune_id not in communes:
                raise ValidationError(
                    _("La commune sélectionnée ne correspond pas au quartier.")
                )

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get("reference", _("Nouveau")) == _("Nouveau"):
                vals["reference"] = self.env["ir.sequence"].next_by_code(
                    "kiiraaye.section"
                ) or _("Nouveau")
        return super().create(vals_list)

    def action_fermer(self):
        for rec in self:
            if rec.state == "fermee":
                continue
            if not rec.motif_fermeture:
                raise UserError(_("Veuillez renseigner le motif de fermeture."))
            rec.write({
                "state": "fermee",
                "date_fermeture": fields.Date.context_today(self),
            })

    def action_ouvrir(self):
        self.write({
            "state": "ouverte",
            "date_fermeture": False,
        })
