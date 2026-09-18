from odoo import api, fields, models


class KiiraayePartisan(models.Model):
    _name = "kiiraaye.partisan"
    _description = "Membre Kiiraaye"
    _rec_name = "nom_complet"
    _order = "nom_complet"

    name = fields.Char(related="nom_complet", store=True, index=True)
    reference = fields.Char(
        string="N° membre",
        required=True,
        copy=False,
        readonly=True,
        default=lambda self: self.env["ir.sequence"].next_by_code(
            "kiiraaye.partisan"
        ) or "Nouveau",
    )
    nom = fields.Char(string="Nom", required=True)
    prenom = fields.Char(string="Prénom", required=True)
    nom_complet = fields.Char(
        string="Nom complet",
        compute="_compute_nom_complet",
        store=True,
    )
    date_naissance = fields.Date(string="Date de naissance")
    lieu_naissance = fields.Char(string="Lieu de naissance")
    national_id = fields.Char(string="N° pièce d'identité")
    country_id = fields.Many2one("res.country", string="Pays", index=True)
    phone = fields.Char(string="Téléphone")
    email = fields.Char(string="E-mail")
    photo = fields.Image(string="Photo")
    active = fields.Boolean(string="Actif", default=True)
    profession_id = fields.Many2one(
        "kiiraaye.profession",
        string="Profession",
        ondelete="restrict",
        index=True,
    )
    cadre_id = fields.Many2one(
        "kiiraaye.cadre",
        string="Ancienne organisation",
        ondelete="restrict",
        index=True,
        copy=False,
    )
    organisation_ids = fields.Many2many(
        "kiiraaye.organisation",
        "kiiraaye_organisation_partisan_rel",
        "partisan_id",
        "organisation_id",
        string="Organisations",
    )
    attachment_ids = fields.Many2many(
        "ir.attachment",
        "kiiraaye_partisan_attachment_rel",
        "partisan_id",
        "attachment_id",
        string="Pièces jointes",
    )
    section_ids = fields.Many2many(
        "kiiraaye.section",
        "kiiraaye_section_partisan_rel",
        "partisan_id",
        "section_id",
        string="Sections / Coordinations",
    )
    attribution_poste_ids = fields.One2many(
        "kiiraaye.attribution.poste",
        "partisan_id",
        string="Postes occupés",
    )
    organisation_banner = fields.Char(
        string="Organisation(s) actuelle(s)",
        compute="_compute_organisation_banner",
    )
    poste_banner = fields.Char(
        string="Poste(s) actuel(s)",
        compute="_compute_member_banners",
    )
    qr_code_value = fields.Char(
        string="Valeur QR",
        compute="_compute_qr_code_value",
        store=True,
    )

    _unique_reference = models.Constraint(
        "UNIQUE(reference)",
        "Le numéro de membre doit être unique.",
    )
    _unique_national_id = models.Constraint(
        "UNIQUE(national_id)",
        "Le numéro de pièce d'identité doit être unique lorsqu'il est renseigné.",
    )

    @api.depends(
        "organisation_ids.name",
        "organisation_ids.type_id.name",
    )
    def _compute_organisation_banner(self):
        for record in self:
            values = []
            for organisation in record.organisation_ids:
                label = organisation.name
                if organisation.type_id:
                    label = f"{organisation.type_id.name} : {organisation.name}"
                values.append(label)
            record.organisation_banner = " • ".join(dict.fromkeys(values))

    @api.depends(
        "attribution_poste_ids.state",
        "attribution_poste_ids.active",
        "attribution_poste_ids.position_id",
        "attribution_poste_ids.position_id.name",
    )
    def _compute_member_banners(self):
        for record in self:
            lines = record.attribution_poste_ids.filtered(
                lambda line: line.state == "validee"
                and line.active
                and line.position_id
            )
            values = []
            for line in lines:
                label = line.position_id.name
                if line.section_id:
                    label = f"{label} — Section : {line.section_id.name}"
                values.append(label)
            record.poste_banner = " • ".join(
                dict.fromkeys(value for value in values if value)
            )

    @api.depends("prenom", "nom")
    def _compute_nom_complet(self):
        for record in self:
            record.nom_complet = " ".join(
                value for value in (record.prenom, record.nom) if value
            )

    @api.depends("reference")
    def _compute_qr_code_value(self):
        """Valeur QR courte et sûre pour la route native /report/barcode."""
        for record in self:
            reference = record.reference or str(record.id or "")
            record.qr_code_value = reference.replace("/", "-").replace(" ", "-")

    def action_print_membership_card(self):
        self.ensure_one()
        return self.env.ref(
            "kiiraaye_governance.action_report_kiiraaye_member_card"
        ).report_action(self)

    def action_open_organisation_assignment(self):
        self.ensure_one()
        action = self.env.ref(
            "kiiraaye_governance.action_kiiraaye_organisation_add_member_wizard"
        ).read()[0]
        action["context"] = dict(
            self.env.context,
            default_partisan_id=self.id,
            default_member_ids=[self.id],
            active_id=self.id,
        )
        return action

    def action_open_cadre_assignment(self):
        self.ensure_one()
        action = self.env.ref(
            "kiiraaye_governance.action_kiiraaye_cadre_assign_wizard"
        ).read()[0]
        action["context"] = dict(
            self.env.context,
            default_partisan_id=self.id,
            active_id=self.id,
        )
        return action

    def action_view_membership_card(self):
        self.ensure_one()
        return self.env.ref(
            "kiiraaye_governance.action_report_kiiraaye_member_card_html"
        ).report_action(self)

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if not vals.get("national_id"):
                vals["national_id"] = False
        return super().create(vals_list)

    def write(self, vals):
        if "national_id" in vals and not vals.get("national_id"):
            vals["national_id"] = False
        return super().write(vals)
