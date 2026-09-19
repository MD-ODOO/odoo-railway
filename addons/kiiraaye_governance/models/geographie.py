from odoo import api, fields, models, _
from odoo.exceptions import ValidationError


class KiiraayeGeographie(models.Model):
    _name = "kiiraaye.geographie"
    _description = "Référentiel géographique Kiiraaye"
    _rec_name = "name"
    _parent_name = "parent_id"
    _parent_store = True
    _order = "niveau, name"

    name = fields.Char(string="Nom", required=True, index=True)
    code = fields.Char(string="Code", index=True)
    country_id = fields.Many2one(
        "res.country",
        string="Pays",
        required=True,
        index=True,
        ondelete="restrict",
    )
    parent_id = fields.Many2one(
        "kiiraaye.geographie",
        string="Zone parente",
        index=True,
        ondelete="restrict",
    )
    parent_path = fields.Char(index=True)
    niveau = fields.Selection(
        [
            ("pays", "Pays"),
            ("niveau1", "Région / État / Province"),
            ("niveau2", "Département / District / Comté"),
            ("niveau3", "Commune / Municipalité / Ville"),
            ("niveau4", "Communauté rurale / niveau local"),
            ("niveau5", "Village / Quartier / Unité locale"),
            ("niveau6", "Sous-quartier / Zone locale"),
            ("localite", "Localité / Autre"),
        ],
        string="Niveau géographique",
        required=True,
        index=True,
    )
    source_admin_level = fields.Selection(
        [
            ("ADM0", "ADM0"),
            ("ADM1", "ADM1"),
            ("ADM2", "ADM2"),
            ("ADM3", "ADM3"),
            ("ADM4", "ADM4"),
            ("ADM5", "ADM5"),
            ("MANUAL", "Manuel"),
        ],
        string="Niveau administratif source",
        index=True,
        help="Niveau administratif original fourni par la source, conservé indépendamment de la normalisation Kiiraaye.",
    )
    designation_locale = fields.Char(
        string="Désignation administrative locale",
        help="Terme utilisé officiellement dans le pays ou la source : province, estado, district, ward, etc.",
    )
    source = fields.Char(string="Source des données")
    source_uid = fields.Char(string="Identifiant source", index=True)
    source_url = fields.Char(string="URL source")
    source_year = fields.Integer(string="Année des données")
    source_license = fields.Char(string="Licence source")
    active = fields.Boolean(string="Actif", default=True)
    child_ids = fields.One2many(
        "kiiraaye.geographie",
        "parent_id",
        string="Sous-zones",
    )

    _unique_source_uid = models.Constraint(
        "UNIQUE(country_id, source_uid)",
        "L'identifiant source doit être unique à l'intérieur d'un pays.",
    )
    _root_shape = models.Constraint(
        "CHECK((niveau = 'pays') = (parent_id IS NULL))",
        "Une zone de niveau Pays doit être une racine et une racine doit être un Pays.",
    )

    @api.constrains("parent_id", "country_id")
    def _check_parent_country(self):
        for record in self:
            if record.parent_id and record.parent_id.country_id != record.country_id:
                raise ValidationError(
                    _("Une zone géographique doit appartenir au même pays que sa zone parente.")
                )
            if record.parent_id == record:
                raise ValidationError(_("Une zone géographique ne peut pas être son propre parent."))

    @api.constrains("niveau", "parent_id")
    def _check_hierarchy(self):
        rank = {
            "pays": 0,
            "niveau1": 1,
            "niveau2": 2,
            "niveau3": 3,
            "niveau4": 4,
            "niveau5": 5,
            "niveau6": 6,
            "localite": 99,
        }
        for record in self:
            if not record.parent_id:
                continue
            parent_rank = rank.get(record.parent_id.niveau, 99)
            current_rank = rank.get(record.niveau, 99)
            if record.niveau == "pays":
                raise ValidationError(_("Un élément de type Pays ne peut pas avoir de parent."))
            if current_rank != 99 and parent_rank != 99 and current_rank <= parent_rank:
                raise ValidationError(
                    _("Le niveau géographique d'une zone enfant doit être inférieur à celui de son parent.")
                )


class ResCountry(models.Model):
    _inherit = "res.country"

    kiiraaye_geographie_ids = fields.One2many(
        "kiiraaye.geographie",
        "country_id",
        string="Géographie Kiiraaye",
    )
