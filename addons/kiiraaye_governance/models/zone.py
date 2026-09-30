from odoo import api, fields, models, _
from odoo.exceptions import ValidationError


class KiiraayeZone(models.Model):
    _name = "kiiraaye.zone"
    _description = "Zone Kiiraaye"
    _rec_name = "name"
    _order = "name, id"

    name = fields.Char(string="Nom de la zone", required=True, index=True)
    reference = fields.Char(
        string="Référence",
        required=True,
        copy=False,
        readonly=True,
        default=lambda self: self.env["ir.sequence"].next_by_code("kiiraaye.zone") or "Nouveau",
    )
    country_id = fields.Many2one(
        "res.country",
        string="Pays",
        required=True,
        default=lambda self: self.env["res.country"].search([("code", "=", "SN")], limit=1),
        ondelete="restrict",
    )
    commune_id = fields.Many2one(
        "kiiraaye.geographie",
        string="Commune",
        required=True,
        ondelete="restrict",
        domain="[('country_id', '=', country_id), ('niveau', '=', 'niveau3'), ('active', '=', True)]",
    )

    # Relations inverses : la zone ne sélectionne plus les quartiers.
    quartier_ids = fields.One2many(
        "kiiraaye.geographie",
        "zone_id",
        string="Quartiers / villages",
        domain="[('country_id', '=', country_id), ('niveau', '=', 'niveau5'), ('active', '=', True)]",
    )
    section_ids = fields.One2many(
        "kiiraaye.section",
        "zone_id",
        string="Sections",
    )
    responsable_user_ids = fields.One2many(
        "res.users",
        "kiiraaye_zone_id",
        string="Responsables de zone",
    )
    active = fields.Boolean(string="Actif", default=True)

    _unique_reference = models.Constraint(
        "UNIQUE(reference)",
        "La référence de la zone doit être unique.",
    )
    _unique_name_commune = models.Constraint(
        "UNIQUE(name, commune_id)",
        "Une zone portant ce nom existe déjà dans cette commune.",
    )

    def init(self):
        """Migre les anciennes affectations M2M vers le nouveau rattachement O2M."""
        super().init()
        self.env.cr.execute("SELECT to_regclass('kiiraaye_zone_quartier_rel')")
        relation_table = self.env.cr.fetchone()[0]
        if relation_table:
            self.env.cr.execute(
                """
                UPDATE kiiraaye_geographie AS g
                   SET zone_id = rel.zone_id
                  FROM kiiraaye_zone_quartier_rel AS rel
                 WHERE g.id = rel.quartier_id
                   AND g.zone_id IS NULL
                   AND g.niveau = 'niveau5'
                """
            )

    @api.onchange("commune_id")
    def _onchange_commune_id(self):
        for quartier in self.quartier_ids:
            if not self._quartier_belongs_to_commune(quartier, self.commune_id):
                quartier.zone_id = False

    @staticmethod
    def _quartier_belongs_to_commune(quartier, commune):
        if not quartier or not commune or quartier.niveau != "niveau5":
            return False
        current = quartier
        while current:
            if current.parent_id == commune:
                return True
            current = current.parent_id
        return False

    @api.constrains("country_id", "commune_id", "quartier_ids", "responsable_user_ids")
    def _check_zone(self):
        for zone in self:
            if zone.commune_id and (
                zone.commune_id.country_id != zone.country_id
                or zone.commune_id.niveau != "niveau3"
            ):
                raise ValidationError(_("La commune de la zone est invalide."))

            invalid = zone.quartier_ids.filtered(
                lambda q: not self._quartier_belongs_to_commune(q, zone.commune_id)
            )
            if invalid:
                raise ValidationError(
                    _("Tous les quartiers d'une zone doivent appartenir à sa commune.")
                )

            invalid_users = zone.responsable_user_ids.filtered(
                lambda u: u.kiiraaye_role != "zone"
            )
            if invalid_users:
                raise ValidationError(
                    _("Tous les responsables d'une zone doivent avoir le rôle Responsable de zone.")
                )

    @api.constrains("quartier_ids")
    def _check_quartier_unique_zone(self):
        for zone in self:
            duplicates = self.env["kiiraaye.geographie"].sudo().search(
                [
                    ("id", "in", zone.quartier_ids.ids),
                    ("zone_id", "!=", zone.id),
                ]
            )
            if duplicates:
                raise ValidationError(
                    _("Un quartier ne peut être rattaché qu'à une seule zone.")
                )

    @api.model_create_multi
    def create(self, vals_list):
        return super().create(vals_list)
