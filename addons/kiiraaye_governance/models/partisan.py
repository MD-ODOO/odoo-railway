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

    @api.depends("prenom", "nom")
    def _compute_nom_complet(self):
        for record in self:
            record.nom_complet = " ".join(
                value for value in (record.prenom, record.nom) if value
            )

    @api.depends("reference", "nom_complet")
    def _compute_qr_code_value(self):
        for record in self:
            record.qr_code_value = "KIR-MEMBRE|%s|%s" % (
                record.reference or "",
                record.nom_complet or "",
            )

    def action_print_membership_card(self):
        self.ensure_one()
        return self.env.ref(
            "kiiraaye_governance.action_report_kiiraaye_member_card"
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
