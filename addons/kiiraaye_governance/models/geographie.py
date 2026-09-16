from odoo import api, fields, models, _
from odoo.exceptions import ValidationError


class KiiraayeGeographie(models.Model):
    _name = "kiiraaye.geographie"
    _description = "Référentiel géographique mondial"
    _parent_store = True
    _parent_name = "parent_id"
    _rec_name = "complete_name"
    _order = "niveau, name"

    name = fields.Char(string="Nom", required=True, index=True)
    code = fields.Char(string="Code", required=True, copy=False, index=True)
    niveau = fields.Selection([
        ("pays", "Pays"),
        ("region", "Région / État / Province"),
        ("departement", "Département / Comté / District"),
        ("commune", "Commune / Municipalité / Ville"),
        ("communaute_rurale", "Communauté rurale / niveau local"),
        ("quartier", "Quartier / District de proximité"),
        ("localite", "Localité / Village"),
        ("autre", "Autre niveau"),
    ], string="Type de niveau", required=True, index=True)
    admin_level = fields.Integer(
        string="Niveau administratif source",
        help="Niveau administratif fourni par la source : ADM0, ADM1, ADM2, etc.",
        index=True,
    )
    parent_id = fields.Many2one(
        "kiiraaye.geographie", string="Parent",
        ondelete="restrict", index=True
    )
    parent_path = fields.Char(index=True)
    child_ids = fields.One2many("kiiraaye.geographie", "parent_id", string="Enfants")
    complete_name = fields.Char(
        compute="_compute_complete_name", store=True, string="Chemin complet"
    )

    # Compatible avec le référentiel d'adresse Odoo.
    country_id = fields.Many2one(
        "res.country", string="Pays", required=True,
        ondelete="restrict", index=True
    )
    state_id = fields.Many2one(
        "res.country.state", string="Région / État / Province",
        ondelete="restrict", index=True,
        help="Correspondance avec la région/état Odoo utilisée par les adresses."
    )

    latitude = fields.Float(string="Latitude", digits=(10, 6))
    longitude = fields.Float(string="Longitude", digits=(10, 6))
    geojson = fields.Text(string="Géométrie GeoJSON")

    source_name = fields.Char(string="Source")
    source_uid = fields.Char(string="Identifiant source", copy=False, index=True)
    source_year = fields.Char(string="Année des données")
    source_license = fields.Char(string="Licence")
    source_url = fields.Char(string="URL / référence source")
    active = fields.Boolean(default=True)

    child_count = fields.Integer(compute="_compute_child_count", readonly=True)

    _code_country_unique = models.Constraint(
        "UNIQUE(code, country_id)",
        "Le code géographique doit être unique dans un pays."
    )
    @api.depends("name", "parent_id.complete_name")
    def _compute_complete_name(self):
        for rec in self:
            rec.complete_name = (
                f"{rec.parent_id.complete_name} / {rec.name}"
                if rec.parent_id else rec.name
            )

    def _compute_child_count(self):
        for rec in self:
            rec.child_count = len(rec.child_ids)

    @api.constrains("parent_id", "country_id", "niveau")
    def _check_hierarchy(self):
        rank = {
            "pays": 0,
            "region": 1,
            "departement": 2,
            "commune": 3,
            "communaute_rurale": 4,
            "quartier": 5,
            "localite": 6,
            "autre": 99,
        }
        for rec in self:
            if rec.parent_id and rec.parent_id.id == rec.id:
                raise ValidationError(_("Une zone géographique ne peut pas être son propre parent."))
            if rec.parent_id:
                if rec.parent_id.country_id != rec.country_id:
                    raise ValidationError(_("Le parent et l'enfant doivent appartenir au même pays."))
                if rec.niveau != "autre" and rec.parent_id.niveau != "autre":
                    if rank.get(rec.niveau, 99) <= rank.get(rec.parent_id.niveau, -1):
                        raise ValidationError(_(
                            "Le niveau géographique de l'enfant doit être inférieur à celui du parent."
                        ))
            if rec.niveau == "pays" and rec.parent_id:
                raise ValidationError(_("Un pays ne peut pas avoir de parent géographique."))

    @api.model
    def get_country_root(self, country):
        return self.search([
            ("niveau", "=", "pays"),
            ("country_id", "=", country.id),
            ("parent_id", "=", False),
        ], limit=1)

    @api.model_create_multi
    def create(self, vals_list):
        records = super().create(vals_list)
        for rec in records:
            if rec.niveau == "pays" and not rec.parent_id and rec.country_id:
                # Unifie le point d'entrée pays avec res.country.
                if not rec.code:
                    rec.code = "COUNTRY-%s" % (rec.country_id.code or rec.country_id.id)
        return records


class ResCountry(models.Model):
    _inherit = "res.country"

    kiiraaye_geographie_ids = fields.One2many(
        "kiiraaye.geographie", "country_id",
        string="Référentiel géographique",
        readonly=True,
    )
    kiiraaye_geographie_count = fields.Integer(
        compute="_compute_kiiraaye_geographie_count"
    )

    def _compute_kiiraaye_geographie_count(self):
        Geo = self.env["kiiraaye.geographie"]
        for rec in self:
            rec.kiiraaye_geographie_count = Geo.search_count([
                ("country_id", "=", rec.id)
            ])
