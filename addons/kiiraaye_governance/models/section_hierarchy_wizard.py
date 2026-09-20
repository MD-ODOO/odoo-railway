from odoo import api, fields, models, _
from odoo.exceptions import UserError


class KiiraayeSectionHierarchyWizard(models.TransientModel):
    _name = "kiiraaye.section.hierarchy.wizard"
    _description = "Hiérarchie géographique d'une section Kiiraay"

    section_id = fields.Many2one(
        "kiiraaye.section",
        string="Section / Coordination",
        required=True,
        readonly=True,
    )
    quartier_id = fields.Many2one(
        "kiiraaye.geographie",
        string="Quartier / Village",
        readonly=True,
    )
    commune_id = fields.Many2one(
        "kiiraaye.geographie",
        string="Commune",
        readonly=True,
    )
    departement_id = fields.Many2one(
        "kiiraaye.geographie",
        string="Département",
        readonly=True,
    )
    region_id = fields.Many2one(
        "kiiraaye.geographie",
        string="Région",
        readonly=True,
    )
    country_id = fields.Many2one(
        "res.country",
        string="Pays",
        readonly=True,
    )

    @api.model
    def default_get(self, fields_list):
        values = super().default_get(fields_list)
        section_id = self.env.context.get("default_section_id") or self.env.context.get("active_id")
        if not section_id:
            raise UserError(_("Aucune section n'a été sélectionnée."))
        section = self.env["kiiraaye.section"].browse(section_id).exists()
        if not section:
            raise UserError(_("La section sélectionnée n'existe plus."))

        def ancestor(record, level):
            current = record
            while current:
                if current.niveau == level:
                    return current
                current = current.parent_id
            return self.env["kiiraaye.geographie"]

        quartier = section.quartier_id
        commune = section.commune_id or ancestor(quartier, "niveau3")
        departement = section.departement_id or ancestor(commune, "niveau2")
        region = section.region_id or ancestor(departement, "niveau1")

        values.update({
            "section_id": section.id,
            "quartier_id": quartier.id or False,
            "commune_id": commune.id or False,
            "departement_id": departement.id or False,
            "region_id": region.id or False,
            "country_id": section.country_id.id or False,
        })
        return values
