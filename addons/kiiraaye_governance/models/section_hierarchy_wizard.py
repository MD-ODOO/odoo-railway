from markupsafe import Markup, escape

from odoo import api, fields, models, _
from odoo.exceptions import UserError


class KiiraayeSectionHierarchyWizard(models.TransientModel):
    _name = "kiiraaye.section.hierarchy.wizard"
    _description = "Hiérarchie d'une section / coordination Kiiraaye"

    section_id = fields.Many2one(
        "kiiraaye.section",
        string="Section / Coordination",
        required=True,
        readonly=True,
    )
    parent_section_id = fields.Many2one(
        "kiiraaye.section",
        string="Niveau supérieur direct",
        readonly=True,
    )
    parent_section_ids = fields.Many2many(
        "kiiraaye.section",
        string="Niveaux supérieurs",
        readonly=True,
    )
    child_section_ids = fields.Many2many(
        "kiiraaye.section",
        string="Sections / coordinations rattachées",
        readonly=True,
    )
    hierarchy_html = fields.Html(
        string="Schéma hiérarchique",
        compute="_compute_hierarchy_html",
        sanitize=True,
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

    def _find_direct_parent(self, section):
        if not section:
            return self.env["kiiraaye.section"]

        domain = [
            ("active", "=", True),
            ("country_id", "=", section.country_id.id),
        ]

        if section.type_section == "regionale":
            domain += [("type_section", "=", "nationale")]
        elif section.type_section == "departementale":
            domain += [
                ("type_section", "=", "regionale"),
                ("region_id", "=", section.region_id.id),
            ]
        elif section.type_section == "communale":
            domain += [
                ("type_section", "=", "departementale"),
                ("region_id", "=", section.region_id.id),
                ("departement_id", "=", section.departement_id.id),
            ]
        else:
            return self.env["kiiraaye.section"]

        return self.env["kiiraaye.section"].search(domain, order="id", limit=1)

    def _find_children(self, section):
        if not section:
            return self.env["kiiraaye.section"]

        domain = [
            ("active", "=", True),
            ("country_id", "=", section.country_id.id),
        ]

        if section.type_section == "nationale":
            domain += [("type_section", "=", "regionale")]
            return self.env["kiiraaye.section"].search(domain, order="name, id")

        if section.type_section == "regionale":
            domain += [
                ("type_section", "=", "departementale"),
                ("region_id", "=", section.region_id.id),
            ]
            return self.env["kiiraaye.section"].search(domain, order="name, id")

        if section.type_section == "departementale":
            domain += [
                ("type_section", "=", "communale"),
                ("region_id", "=", section.region_id.id),
                ("departement_id", "=", section.departement_id.id),
            ]
            return self.env["kiiraaye.section"].search(domain, order="name, id")

        return self.env["kiiraaye.section"]

    def _section_card(self, section, current=False):
        type_labels = dict(self.env["kiiraaye.section"]._fields["type_section"].selection)
        type_name = type_labels.get(section.type_section, section.type_section or "")
        coordinator = section.cordonnateur_id.nom_complet if section.cordonnateur_id else _("Non renseigné")
        member_count = section.member_count or 0
        state_name = _("Ouverte") if section.state == "ouverte" else _("Fermée")
        classes = "k_section_hierarchy_card k_section_hierarchy_current" if current else "k_section_hierarchy_card"
        return Markup(
            '<div class="%s">'
            '<div class="k_section_hierarchy_card_title">%s</div>'
            '<div class="k_section_hierarchy_card_type">%s</div>'
            '<div class="k_section_hierarchy_card_meta">'
            '<span>%s : %s</span>'
            '<span>%s : %s</span>'
            '<span>%s</span>'
            '</div>'
            '</div>'
        ) % (
            classes,
            escape(section.name or ""),
            escape(type_name or ""),
            escape(_("Coordonnateur")),
            escape(coordinator or ""),
            escape(_("Membres")),
            escape(str(member_count)),
            escape(state_name),
        )

    @api.depends("section_id")
    def _compute_hierarchy_html(self):
        Section = self.env["kiiraaye.section"]
        for wizard in self:
            section = wizard.section_id
            if not section:
                wizard.hierarchy_html = Markup(
                    '<div class="k_section_hierarchy_empty">%s</div>'
                ) % escape(_("Enregistrez la section pour afficher sa hiérarchie."))
                continue

            chain = []
            current = section
            seen = set()
            while current and current.id not in seen:
                seen.add(current.id)
                parent = wizard._find_direct_parent(current)
                if not parent:
                    break
                chain.append(parent)
                current = parent

            children = wizard._find_children(section)
            wizard.parent_section_id = chain[0].id if chain else False
            wizard.parent_section_ids = [(6, 0, [record.id for record in reversed(chain)])]
            wizard.child_section_ids = [(6, 0, children.ids)]

            upper = list(reversed(chain))
            upper_html = Markup("").join(wizard._section_card(record) for record in upper)
            child_html = Markup("").join(wizard._section_card(record) for record in children)

            if not upper_html:
                upper_html = Markup(
                    '<div class="k_section_hierarchy_root">%s</div>'
                ) % escape(_("Niveau supérieur non défini"))

            if not child_html:
                child_html = Markup(
                    '<div class="k_section_hierarchy_root">%s</div>'
                ) % escape(_("Aucune section / coordination rattachée"))

            wizard.hierarchy_html = Markup(
                '<div class="k_section_hierarchy_canvas">'
                '<div class="k_section_hierarchy_level_label">%s</div>'
                '<div class="k_section_hierarchy_level k_section_hierarchy_up">%s</div>'
                '<div class="k_section_hierarchy_connector">↓</div>'
                '<div class="k_section_hierarchy_level_label">%s</div>'
                '<div class="k_section_hierarchy_level k_section_hierarchy_center">%s</div>'
                '<div class="k_section_hierarchy_connector">↓</div>'
                '<div class="k_section_hierarchy_level_label">%s</div>'
                '<div class="k_section_hierarchy_level k_section_hierarchy_down">%s</div>'
                '</div>'
            ) % (
                escape(_("Niveaux supérieurs")),
                upper_html,
                escape(_("Section / coordination sélectionnée")),
                wizard._section_card(section, current=True),
                escape(_("Sections / coordinations rattachées")),
                child_html,
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
