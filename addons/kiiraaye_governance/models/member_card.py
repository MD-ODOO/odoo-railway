import secrets
from odoo import api, fields, models, _
from odoo.exceptions import UserError


class KiiraayeMemberCard(models.Model):
    _name = "kiiraaye.member.card"
    _description = "Carte de membre Kiiraaye"
    _inherit = ["mail.thread", "mail.activity.mixin"]
    _order = "id desc"

    name = fields.Char(
        string="Référence carte", required=True, copy=False, index=True,
        default="Nouvelle carte"
    )
    partisan_id = fields.Many2one(
        "kiiraaye.partisan", string="Partisan", required=True,
        ondelete="restrict", index=True
    )
    territoire_id = fields.Many2one(
        related="partisan_id.territoire_id", store=True, index=True,
        string="Territoire"
    )
    matricule = fields.Char(
        related="partisan_id.matricule", store=True, readonly=True,
        string="Matricule"
    )
    section_id = fields.Many2one(
        related="partisan_id.section_id", store=True, string="Section"
    )
    poste_id = fields.Many2one(
        related="partisan_id.poste_actuel_id", store=True,
        string="Poste actuel"
    )
    photo = fields.Image(
        related="partisan_id.photo", string="Photo", readonly=True
    )
    date_emission = fields.Date(
        string="Date d'émission", default=fields.Date.context_today,
        required=True
    )
    date_expiration = fields.Date(string="Date d'expiration")
    state = fields.Selection([
        ("draft", "Brouillon"),
        ("active", "Active"),
        ("expired", "Expirée"),
        ("cancelled", "Annulée"),
    ], default="draft", required=True, tracking=True)
    qr_value = fields.Char(
        string="Code QR", compute="_compute_qr_value", store=True
    )
    verification_token = fields.Char(
        string="Jeton de vérification", copy=False, index=True,
        readonly=True
    )

    _sql_constraints = [
        ("name_unique", "unique(name)",
         "La référence de carte doit être unique."),
        ("verification_token_unique", "unique(verification_token)",
         "Le jeton de vérification doit être unique."),
    ]

    @api.depends("verification_token")
    def _compute_qr_value(self):
        base_url = self.env["ir.config_parameter"].sudo().get_param(
            "web.base.url", default=""
        )
        for rec in self:
            rec.qr_value = (
                f"{base_url}/kiiraaye/card/verify/{rec.verification_token}"
                if rec.verification_token else ""
            )

    @api.model_create_multi
    def create(self, vals_list):
        sequence = self.env["ir.sequence"]
        for vals in vals_list:
            if vals.get("name") == "Nouvelle carte":
                vals["name"] = sequence.next_by_code(
                    "kiiraaye.member.card"
                ) or "Nouvelle carte"
            if not vals.get("verification_token"):
                vals["verification_token"] = secrets.token_urlsafe(24)
        return super().create(vals_list)

    def action_activate(self):
        for rec in self:
            if rec.partisan_id.section_id.state != "ouverte":
                raise UserError(
                    _("La carte ne peut pas être activée : la section du partisan est fermée.")
                )
            rec.write({"state": "active"})

    def action_cancel(self):
        self.write({"state": "cancelled"})

    def action_expire(self):
        self.write({"state": "expired"})

    def action_print(self):
        self.ensure_one()
        if self.state == "cancelled":
            raise UserError(_("Une carte annulée ne peut pas être imprimée."))
        return self.env.ref(
            "kiiraaye_governance.action_report_member_card"
        ).report_action(self)
