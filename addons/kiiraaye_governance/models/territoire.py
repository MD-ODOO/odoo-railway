from odoo import api, fields, models, _
from odoo.exceptions import ValidationError

class KiiraayeTerritoire(models.Model):
    _name = "kiiraaye.territoire"
    _description = "Référentiel géographique Kiiraaye"
    _parent_store = True
    _parent_name = "parent_id"
    _rec_name = "complete_name"
    _order = "type_niveau, name"

    name = fields.Char(string="Nom", required=True, index=True)
    code = fields.Char(string="Code", required=True, copy=False, index=True)
    type_niveau = fields.Selection([
        ("pays", "Pays"),
        ("region", "Région / État / Province"),
        ("departement", "Département / Comté"),
        ("commune", "Commune / Municipalité"),
        ("communaute_rurale", "Communauté rurale / niveau local"),
        ("quartier", "Quartier / District local"),
        ("autre", "Autre niveau"),
    ], required=True, index=True)
    admin_level = fields.Integer(
        string="Niveau source",
        default=0,
        help="Niveau administratif de la source (ADM0 à ADM5)."
    )
    parent_id = fields.Many2one(
        "kiiraaye.territoire", string="Parent",
        ondelete="restrict", index=True
    )
    parent_path = fields.Char(index=True)
    child_ids = fields.One2many("kiiraaye.territoire", "parent_id")
    complete_name = fields.Char(
        compute="_compute_complete_name", store=True, string="Nom complet"
    )
    country_id = fields.Many2one(
        "res.country", string="Pays", index=True, ondelete="restrict"
    )
    source_name = fields.Char(string="Source")
    source_uid = fields.Char(string="ID source", copy=False, index=True)
    source_year = fields.Char(string="Année des données")
    source_license = fields.Char(string="Licence")
    source_url = fields.Char(string="URL source")
    latitude = fields.Float(string="Latitude", digits=(10, 6))
    longitude = fields.Float(string="Longitude", digits=(10, 6))
    geojson = fields.Text(string="Géométrie GeoJSON")
    population_reference = fields.Integer(string="Population de référence")
    active = fields.Boolean(default=True)
    bureau_id = fields.Many2one("kiiraaye.bureau", string="Bureau")
    responsable_ids = fields.Many2many(
        "res.users", "kiiraaye_territoire_user_rel",
        "territoire_id", "user_id", string="Responsables"
    )
    partisan_count = fields.Integer(compute="_compute_counts")
    section_count = fields.Integer(compute="_compute_counts")

    _sql_constraints = [
        ("code_unique", "unique(code)", "Le code du territoire doit être unique."),
    ]

    @api.depends("name", "parent_id.complete_name")
    def _compute_complete_name(self):
        for rec in self:
            rec.complete_name = (
                f"{rec.parent_id.complete_name} / {rec.name}"
                if rec.parent_id else rec.name
            )

    def _compute_counts(self):
        Partisan = self.env["kiiraaye.partisan"]
        Section = self.env["kiiraaye.section"]
        for rec in self:
            rec.partisan_count = Partisan.search_count(
                [("territoire_id", "child_of", rec.id)]
            )
            rec.section_count = Section.search_count(
                [("territoire_id", "child_of", rec.id)]
            )

    @api.constrains("admin_level")
    def _check_admin_level(self):
        for rec in self:
            if rec.admin_level < 0 or rec.admin_level > 10:
                raise ValidationError(_("Le niveau source doit être compris entre 0 et 10."))

    @api.model
    def create_country_root(self, country):
        self.ensure_one()
        return self.create({
            "name": country.name,
            "code": country.code or country.id,
            "type_niveau": "pays",
            "admin_level": 0,
            "country_id": country.id,
            "source_name": "Odoo res.country",
        })
