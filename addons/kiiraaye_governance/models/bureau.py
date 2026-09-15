from odoo import api, fields, models, _

class KiiraayeBureau(models.Model):
    _name = "kiiraaye.bureau"
    _description = "Bureau exécutif territorial"
    _inherit = ["mail.thread", "mail.activity.mixin"]
    _order = "territoire_id"

    name = fields.Char(string="Nom", compute="_compute_name", store=True)
    territoire_id = fields.Many2one(
        "kiiraaye.territoire", string="Territoire",
        required=True, ondelete="restrict", index=True
    )
    poste_ids = fields.One2many(
        "kiiraaye.poste", "bureau_id", string="Postes / mandats"
    )
    membre_ids = fields.Many2many(
        "kiiraaye.partisan", compute="_compute_membres",
        string="Membres du bureau"
    )
    coordonnateur_id = fields.Many2one(
        "kiiraaye.partisan", compute="_compute_coordonnateur",
        string="Coordonnateur", store=True
    )
    active = fields.Boolean(default=True, tracking=True)
    date_creation = fields.Date(
        default=fields.Date.context_today, string="Date de création"
    )

    _sql_constraints = [
        ("territoire_unique", "unique(territoire_id)",
         "Un seul bureau actif/référent est autorisé par territoire."),
    ]

    @api.depends("territoire_id.complete_name")
    def _compute_name(self):
        for rec in self:
            rec.name = _("Bureau - %s") % (rec.territoire_id.complete_name or "")

    @api.depends("poste_ids.partisan_id", "poste_ids.state", "poste_ids.type_poste")
    def _compute_membres(self):
        for rec in self:
            rec.membre_ids = rec.poste_ids.filtered(
                lambda p: p.state == "actif"
            ).mapped("partisan_id")

    @api.depends("poste_ids.partisan_id", "poste_ids.state", "poste_ids.type_poste")
    def _compute_coordonnateur(self):
        for rec in self:
            poste = rec.poste_ids.filtered(
                lambda p: p.state == "actif" and p.type_poste == "coordonnateur"
            )[:1]
            rec.coordonnateur_id = poste.partisan_id if poste else False
