from odoo import api, fields, models, _
from odoo.exceptions import UserError, ValidationError


class KiiraayeAttributionPoste(models.Model):
    _name = "kiiraaye.attribution.poste"
    _description = "Attribution d'un poste à un membre Kiiraaye"
    _rec_name = "reference"
    _order = "date_attribution desc, id desc"

    reference = fields.Char(
        string="Référence",
        required=True,
        copy=False,
        readonly=True,
        default=lambda self: self.env["ir.sequence"].next_by_code(
            "kiiraaye.attribution.poste"
        ) or "Nouveau",
    )
    position_id = fields.Many2one(
        "kiiraaye.position",
        string="Poste",
        required=True,
        ondelete="restrict",
    )
    section_id = fields.Many2one(
        "kiiraaye.section",
        string="Section / Coordination",
        required=True,
        ondelete="restrict",
    )
    partisan_id = fields.Many2one(
        "kiiraaye.partisan",
        string="Membre de la section",
        required=True,
        ondelete="restrict",
    )
    date_attribution = fields.Date(
        string="Date",
        required=True,
        default=fields.Date.context_today,
    )
    pv_file = fields.Binary(string="PV", attachment=True, copy=False)
    pv_filename = fields.Char(string="Nom du fichier PV", copy=False)
    state = fields.Selection(
        [
            ("brouillon", "Brouillon"),
            ("validee", "Validée"),
            ("annulee", "Annulée"),
        ],
        string="État",
        default="brouillon",
        required=True,
        copy=False,
    )
    active = fields.Boolean(string="Actif", default=True)
    validation_uid = fields.Many2one(
        "res.users",
        string="Validée par",
        readonly=True,
        copy=False,
    )
    validation_date = fields.Datetime(
        string="Date de validation",
        readonly=True,
        copy=False,
    )

    @api.onchange("section_id")
    def _onchange_section_id(self):
        if self.partisan_id and self.section_id not in self.partisan_id.section_ids:
            self.partisan_id = False
        return {
            "domain": {
                "partisan_id": (
                    [("section_ids", "in", self.section_id.id)]
                    if self.section_id
                    else [("id", "=", False)]
                )
            }
        }

    @api.constrains("section_id", "partisan_id")
    def _check_member_section(self):
        for record in self:
            if record.section_id and record.partisan_id:
                if record.section_id not in record.partisan_id.section_ids:
                    raise ValidationError(
                        _(
                            "Le membre sélectionné doit appartenir à la section / coordination choisie."
                        )
                    )

    @api.constrains("position_id", "section_id", "partisan_id", "state")
    def _check_active_position(self):
        for record in self.filtered(lambda r: r.state == "validee"):
            duplicate = self.env["kiiraaye.attribution.poste"].search(
                [
                    ("id", "!=", record.id),
                    ("position_id", "=", record.position_id.id),
                    ("section_id", "=", record.section_id.id),
                    ("state", "=", "validee"),
                ],
                limit=1,
            )
            if duplicate:
                raise ValidationError(
                    _(
                        "Le poste « %s » est déjà attribué et validé dans cette section / coordination."
                    )
                    % record.position_id.name
                )

    def action_validate(self):
        self.ensure_one()
        if self.state != "brouillon":
            raise UserError(_("Seule une attribution en brouillon peut être validée."))
        if self.partisan_id not in self.section_id.membre_ids:
            raise UserError(
                _("Le membre doit appartenir à la section / coordination avant validation.")
            )

        duplicate = self.env["kiiraaye.attribution.poste"].search(
            [
                ("id", "!=", self.id),
                ("position_id", "=", self.position_id.id),
                ("section_id", "=", self.section_id.id),
                ("state", "=", "validee"),
            ],
            limit=1,
        )
        if duplicate:
            raise UserError(
                _(
                    "Le poste « %s » est déjà attribué à %s dans cette section / coordination."
                )
                % (self.position_id.name, duplicate.partisan_id.nom_complet)
            )

        BureauLine = self.env["kiiraaye.bureau.ligne"]
        existing_line = BureauLine.search(
            [
                ("section_id", "=", self.section_id.id),
                ("position_id", "=", self.position_id.id),
                ("partisan_id", "=", self.partisan_id.id),
            ],
            limit=1,
        )
        if existing_line:
            existing_line.write({"active": True})
        else:
            BureauLine.create(
                {
                    "section_id": self.section_id.id,
                    "position_id": self.position_id.id,
                    "partisan_id": self.partisan_id.id,
                    "date_debut": self.date_attribution,
                    "active": True,
                }
            )

        self.write(
            {
                "state": "validee",
                "validation_uid": self.env.user.id,
                "validation_date": fields.Datetime.now(),
            }
        )
        return True

    def action_cancel(self):
        for record in self:
            if record.state == "validee":
                bureau_line = self.env["kiiraaye.bureau.ligne"].search(
                    [
                        ("section_id", "=", record.section_id.id),
                        ("position_id", "=", record.position_id.id),
                        ("partisan_id", "=", record.partisan_id.id),
                        ("active", "=", True),
                    ],
                    limit=1,
                )
                if bureau_line:
                    bureau_line.write(
                        {
                            "active": False,
                            "date_fin": fields.Date.context_today(self),
                        }
                    )
            record.write({"state": "annulee", "active": False})
        return True

    def unlink(self):
        if any(record.state == "validee" for record in self):
            raise UserError(
                _("Une attribution déjà validée ne peut pas être supprimée. Annulez-la à la place.")
            )
        return super().unlink()
