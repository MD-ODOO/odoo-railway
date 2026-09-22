from odoo import api, fields, models, _
from odoo.exceptions import ValidationError


class KiiraayeElection(models.Model):
    _name = "kiiraaye.election"
    _description = "Historique des élections"
    _rec_name = "name"
    _order = "date desc, id desc"

    name = fields.Char(string="Élection", required=True, index=True)
    date = fields.Date(string="Date du scrutin", required=True, index=True)
    election_type = fields.Selection(
        [
            ("presidentielle", "Présidentielle"),
            ("legislative", "Législative"),
            ("locale", "Locale"),
            ("referendum", "Référendum"),
            ("autre", "Autre"),
        ],
        string="Type",
        required=True,
        default="presidentielle",
    )
    source = fields.Char(string="Source", required=True)
    source_url = fields.Char(string="URL source")
    notes = fields.Text(string="Notes")
    active = fields.Boolean(string="Actif", default=True)
    result_ids = fields.One2many(
        "kiiraaye.election.result",
        "election_id",
        string="Résultats territoriaux",
    )

    _unique_election = models.Constraint(
        "UNIQUE(name, date)",
        "Cette élection existe déjà pour cette date.",
    )


class KiiraayeElectionResult(models.Model):
    _name = "kiiraaye.election.result"
    _description = "Résultat électoral historique"
    _rec_name = "display_name"
    _order = "election_id, geographie_id"

    election_id = fields.Many2one(
        "kiiraaye.election",
        string="Élection",
        required=True,
        ondelete="cascade",
        index=True,
    )
    scope = fields.Selection(
        [
            ("global", "Résultat global"),
            ("geographique", "Résultat géographique"),
        ],
        string="Portée",
        required=True,
        default="geographique",
        index=True,
    )
    geographie_id = fields.Many2one(
        "kiiraaye.geographie",
        string="Région / Département / Commune",
        ondelete="cascade",
        index=True,
    )
    registered_voters = fields.Integer(
        string="Électeurs inscrits",
        default=0,
    )
    voters = fields.Integer(
        string="Votants",
        default=0,
    )
    null_votes = fields.Integer(
        string="Bulletins nuls / blancs",
        default=0,
    )
    valid_votes = fields.Integer(
        string="Suffrages valablement exprimés",
        default=0,
    )
    source = fields.Char(string="Source")
    notes = fields.Text(string="Notes")
    display_name = fields.Char(
        string="Libellé",
        compute="_compute_display_name",
    )

    @api.depends("election_id.name", "geographie_id.name", "scope")
    def _compute_display_name(self):
        for record in self:
            if record.scope == "global":
                record.display_name = f"{record.election_id.name or ''} — Global"
            else:
                record.display_name = (
                    f"{record.election_id.name or ''} — "
                    f"{record.geographie_id.name or 'Zone'}"
                )

    @api.constrains(
        "scope",
        "geographie_id",
        "registered_voters",
        "voters",
        "null_votes",
        "valid_votes",
    )
    def _check_result_values(self):
        for record in self:
            if record.scope == "global" and record.geographie_id:
                raise ValidationError(
                    _("Un résultat global ne doit pas avoir de zone géographique.")
                )
            if record.scope == "geographique" and not record.geographie_id:
                raise ValidationError(
                    _("Un résultat géographique doit être rattaché à une zone.")
                )
            for field_name in (
                "registered_voters",
                "voters",
                "null_votes",
                "valid_votes",
            ):
                if getattr(record, field_name) < 0:
                    raise ValidationError(
                        _("Les valeurs électorales ne peuvent pas être négatives.")
                    )
            if record.voters > record.registered_voters and record.registered_voters:
                raise ValidationError(
                    _("Le nombre de votants ne peut pas dépasser les inscrits.")
                )
            if record.valid_votes > record.voters and record.voters:
                raise ValidationError(
                    _("Les suffrages valablement exprimés ne peuvent pas dépasser les votants.")
                )

    def participation_pct(self):
        self.ensure_one()
        return (
            round(self.voters / self.registered_voters * 100, 2)
            if self.registered_voters
            else 0.0
        )

    def valid_pct_of_voters(self):
        self.ensure_one()
        return (
            round(self.valid_votes / self.voters * 100, 2)
            if self.voters
            else 0.0
        )
