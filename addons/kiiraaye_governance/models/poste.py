from odoo import api, fields, models, _
from odoo.exceptions import ValidationError

class KiiraayePoste(models.Model):
    _name = "kiiraaye.poste"
    _description = "Attribution nominative d'un poste"
    _order = "date_debut desc, id desc"

    bureau_id = fields.Many2one(
        "kiiraaye.bureau", string="Bureau", required=True,
        ondelete="restrict", index=True
    )
    section_id = fields.Many2one(
        "kiiraaye.section", string="Section / Coordination",
        related="bureau_id.section_id", store=True, index=True
    )
    geographie_id = fields.Many2one(
        related="bureau_id.geographie_id", store=True, index=True
    )
    position_id = fields.Many2one(
        "kiiraaye.position", string="Fonction", required=True,
        ondelete="restrict"
    )
    partisan_id = fields.Many2one(
        "kiiraaye.partisan", string="Partisan", required=True,
        ondelete="restrict"
    )
    date_debut = fields.Date(
        string="Date de début", required=True,
        default=fields.Date.context_today
    )
    date_fin = fields.Date(string="Date de fin")
    pv_election = fields.Binary(string="PV d'élection (PDF)", attachment=True)
    pv_election_filename = fields.Char()
    photo = fields.Image(string="Photo", attachment=True)
    state = fields.Selection([
        ("actif", "Actif"),
        ("termine", "Terminé"),
        ("revoque", "Révoqué"),
    ], default="actif", required=True, tracking=True)

    @api.constrains("date_debut", "date_fin")
    def _check_dates(self):
        for rec in self:
            if rec.date_fin and rec.date_fin < rec.date_debut:
                raise ValidationError(
                    _("La date de fin doit être postérieure à la date de début.")
                )

    @api.constrains("partisan_id", "bureau_id", "position_id")
    def _check_partisan_territory(self):
        for rec in self:
            if not rec.partisan_id or not rec.bureau_id or not rec.position_id:
                continue
            bureau_territory = rec.bureau_id.geographie_id
            member_territory = rec.partisan_id.geographie_id

            # Le titulaire doit appartenir au  geographie du bureau
            # ou à l'un de ses sous- geographies.
            if member_territory not in bureau_territory.search(
                [("id", "child_of", bureau_territory.id)]
            ):
                raise ValidationError(
                    _("Le partisan n'appartient pas au périmètre géographique du bureau.")
                )

    @api.constrains("bureau_id", "position_id", "state")
    def _check_unique_active(self):
        for rec in self:
            if rec.state != "actif":
                continue
            duplicate = self.search_count([
                ("id", "!=", rec.id),
                ("bureau_id", "=", rec.bureau_id.id),
                ("position_id", "=", rec.position_id.id),
                ("state", "=", "actif"),
            ])
            if duplicate:
                raise ValidationError(
                    _("Ce poste possède déjà un titulaire actif dans ce bureau.")
                )

    @api.model_create_multi
    def create(self, vals_list):
        records = super().create(vals_list)
        for rec in records.filtered(lambda r: r.state == "actif"):
            previous = self.search([
                ("id", "!=", rec.id),
                ("bureau_id", "=", rec.bureau_id.id),
                ("position_id", "=", rec.position_id.id),
                ("state", "=", "actif"),
                ("date_debut", "<=", rec.date_debut),
            ], order="date_debut desc, id desc", limit=1)
            if previous:
                previous.write({
                    "state": "termine",
                    "date_fin": rec.date_debut,
                })
        return records
