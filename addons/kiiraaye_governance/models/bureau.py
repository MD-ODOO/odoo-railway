from odoo import api, fields, models, _


class KiiraayeBureau(models.Model):
    _name = "kiiraaye.bureau"
    _description = "Bureau de section / coordination"
    _inherit = ["mail.thread", "mail.activity.mixin"]
    _order = "section_id"

    name = fields.Char(string="Nom", compute="_compute_name", store=True)
    section_id = fields.Many2one(
        "kiiraaye.section", string="Section / Coordination",
        required=True, ondelete="cascade", index=True
    )
    geographie_id = fields.Many2one(
        "kiiraaye.geographie", string="Lieu / Zone",
        related="section_id.lieu_id", store=True, readonly=True, index=True
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
    date_creation = fields.Date(default=fields.Date.context_today, string="Date de création")

    _section_unique = models.Constraint(
        "UNIQUE(section_id)",
        "Une section/coordination ne peut avoir qu'un seul bureau de référence."
    )
    @api.depends("section_id.name", "section_id.type_section")
    def _compute_name(self):
        for rec in self:
            label = dict(self.env["kiiraaye.section"].fields_get(["type_section"])["type_section"]["selection"])
            rec.name = _("Bureau %s - %s") % (label.get(rec.section_id.type_section, ""), rec.section_id.name or "")

    @api.depends("poste_ids.partisan_id", "poste_ids.state", "poste_ids.position_id")
    def _compute_membres(self):
        for rec in self:
            rec.membre_ids = rec.poste_ids.filtered(lambda p: p.state == "actif").mapped("partisan_id")

    @api.depends("poste_ids.partisan_id", "poste_ids.state", "poste_ids.position_id")
    def _compute_coordonnateur(self):
        for rec in self:
            poste = rec.poste_ids.filtered(
                lambda p: p.state == "actif" and p.position_id.code == "coordonnateur"
            )[:1]
            rec.coordonnateur_id = poste.partisan_id if poste else False
