# -*- coding: utf-8 -*-
from odoo import api, fields, models, _, Command
from odoo.exceptions import UserError


class SmartStudentParent(models.Model):
    _name = "smart.student.parent"
    _description = "Parent / Tuteur SMART"
    _order = "last_name, first_name"

    first_name = fields.Char(string="Prénom")
    last_name = fields.Char(string="Nom", required=True)
    name = fields.Char(string="Nom complet", compute="_compute_name", store=True)
    phone = fields.Char(string="Téléphone")
    email = fields.Char(string="Email")
    street = fields.Char(string="Adresse")
    profession = fields.Char(string="Profession")
    relation = fields.Selection([
        ("father", "Père"), ("mother", "Mère"), ("guardian", "Tuteur"), ("other", "Autre")
    ], string="Lien avec l'étudiant", default="guardian")
    partner_id = fields.Many2one("res.partner", string="Partenaire comptable", ondelete="set null")
    student_id = fields.Many2one("smart.student", string="Étudiant", required=True, ondelete="cascade", index=True)
    active = fields.Boolean(default=True)

    @api.depends("last_name", "first_name")
    def _compute_name(self):
        for rec in self:
            rec.name = " ".join(x for x in [rec.first_name, rec.last_name] if x)

    def action_create_partner(self):
        for rec in self:
            if not rec.partner_id:
                rec.partner_id = self.env["res.partner"].create({
                    "name": rec.name or rec.last_name,
                    "email": rec.email,
                    "phone": rec.phone,
                    "street": rec.street,
                    "customer_rank": 1,
                })
        return True


class SmartStudent(models.Model):
    _name = "smart.student"
    _description = "Étudiant SMART"
    _inherit = ["mail.thread", "mail.activity.mixin"]
    _order = "create_date desc"

    name = fields.Char(string="Nom complet", compute="_compute_name", store=True)
    last_name = fields.Char(string="Nom", required=True, tracking=True)
    first_name = fields.Char(string="Prénoms", required=True, tracking=True)
    birthdate = fields.Date(string="Date de naissance")
    birth_place = fields.Char(string="Lieu de naissance")
    phone = fields.Char(string="Téléphone")
    email = fields.Char(string="Adresse email")
    street = fields.Char(string="Adresse domicile")
    nationality_id = fields.Many2one("res.country", string="Nationalité")
    photo = fields.Image(string="Photo")
    study_level = fields.Selection([
        ("bac", "Bac"), ("bac1", "Bac + 1"), ("bac2", "Bac + 2"),
        ("bac3", "Bac + 3"), ("bac4", "Bac + 4"), ("bac5", "Bac + 5"), ("other", "Autre")
    ], string="Niveau d'études")
    study_domain = fields.Char(string="Domaine d'études")
    current_school = fields.Char(string="Établissement scolaire actuel")
    current_employer = fields.Char(string="Employeur")
    hobbies = fields.Char(string="Loisirs")
    studies_requested = fields.Text(string="Études sollicitées")
    school_type = fields.Selection([
        ("public", "École publique"), ("private", "École privée")
    ], string="Type d'établissement souhaité")
    destination_country_ids = fields.Many2many("res.country", string="Pays sollicités")
    destination_cities = fields.Char(string="Villes sollicitées")
    campus_email = fields.Char(string="Email Campus")
    campus_password = fields.Char(string="Mot de passe Campus", copy=False)
    parent_ids = fields.One2many("smart.student.parent", "student_id", string="Parents / Tuteurs")
    referral_name = fields.Char(string="Personne ayant donné le contact")
    referral_phone = fields.Char(string="Téléphone du contact")
    partner_id = fields.Many2one("res.partner", string="Partenaire comptable", copy=False)
    active = fields.Boolean(default=True)
    application_ids = fields.One2many("smart.student.application", "student_id", string="Dossiers")
    application_count = fields.Integer(compute="_compute_counts")

    @api.depends("last_name", "first_name")
    def _compute_name(self):
        for rec in self:
            rec.name = " ".join(x for x in [rec.first_name, rec.last_name] if x)

    def _compute_counts(self):
        for rec in self:
            rec.application_count = len(rec.application_ids)

    def action_create_partner(self):
        for rec in self:
            if not rec.partner_id:
                rec.partner_id = self.env["res.partner"].create({
                    "name": rec.name,
                    "email": rec.email,
                    "phone": rec.phone,
                    "street": rec.street,
                    "image_1920": rec.photo,
                    "customer_rank": 1,
                })
        return True

    def get_or_create_partner(self):
        self.ensure_one()
        self.action_create_partner()
        if not self.partner_id:
            raise UserError(_("Impossible de créer le partenaire comptable de l'étudiant."))
        return self.partner_id

    def action_open_applications(self):
        self.ensure_one()
        return {
            "type": "ir.actions.act_window", "name": _("Dossiers de %s") % self.name,
            "res_model": "smart.student.application", "view_mode": "list,form",
            "domain": [("student_id", "=", self.id)], "context": {"default_student_id": self.id},
        }

    def action_new_application(self):
        self.ensure_one()
        return {
            "type": "ir.actions.act_window", "name": _("Nouveau dossier"),
            "res_model": "smart.student.application", "view_mode": "form",
            "context": {"default_student_id": self.id},
        }


class SmartServicePackage(models.Model):
    _name = "smart.service.package"
    _description = "Formule d'accompagnement SMART"
    _order = "country_id, name"

    name = fields.Char(required=True)
    active = fields.Boolean(default=True)
    country_id = fields.Many2one("res.country", string="Pays", required=True)
    application_type = fields.Selection([
        ("preinscription", "Préinscription"), ("inscription", "Inscription"),
        ("both", "Préinscription + inscription")
    ], string="Type de procédure", default="preinscription", required=True)
    fee_ids = fields.One2many("smart.service.fee", "package_id", string="Frais")
    currency_id = fields.Many2one("res.currency", default=lambda self: self.env.company.currency_id, required=True)
    total_amount = fields.Monetary(compute="_compute_totals", currency_field="currency_id", store=True)
    smart_amount = fields.Monetary(compute="_compute_totals", currency_field="currency_id", store=True)
    external_amount = fields.Monetary(compute="_compute_totals", currency_field="currency_id", store=True)
    note = fields.Text()

    @api.depends("fee_ids.amount", "fee_ids.is_external")
    def _compute_totals(self):
        for rec in self:
            rec.total_amount = sum(rec.fee_ids.mapped("amount"))
            rec.external_amount = sum(rec.fee_ids.filtered("is_external").mapped("amount"))
            rec.smart_amount = rec.total_amount - rec.external_amount


class SmartServiceFee(models.Model):
    _name = "smart.service.fee"
    _description = "Frais d'accompagnement SMART"
    _order = "sequence, id"

    sequence = fields.Integer(default=10)
    package_id = fields.Many2one("smart.service.package", required=True, ondelete="cascade")
    name = fields.Char(string="Libellé", required=True)
    fee_type = fields.Selection([
        ("dossier", "Frais de dossier"), ("honoraires", "Honoraires"),
        ("campus", "Campus / plateforme"), ("visa", "Visa / immigration"), ("other", "Autre")
    ], string="Type de frais", default="dossier", required=True)
    product_id = fields.Many2one("product.product", string="Produit comptable")
    amount = fields.Monetary(required=True, currency_field="currency_id")
    currency_id = fields.Many2one(related="package_id.currency_id", store=True, readonly=True)
    is_external = fields.Boolean(string="Frais externe / à la charge de l'étudiant")
    invoiceable = fields.Boolean(string="Facturable par SMART", default=True)
    stage = fields.Selection([
        ("registration", "Inscription"), ("admission", "Préinscription / admission"),
        ("caq", "CAQ"), ("visa", "Visa / immigration"), ("other", "Autre")
    ], string="Étape", default="admission")
    note = fields.Text()


class SmartDocumentType(models.Model):
    _name = "smart.document.type"
    _description = "Type de pièce SMART"
    _order = "sequence, name"

    name = fields.Char(required=True)
    sequence = fields.Integer(default=10)
    active = fields.Boolean(default=True)
    required_for_admission = fields.Boolean(string="Requis admission")
    required_for_visa = fields.Boolean(string="Requis visa")
    country_id = fields.Many2one("res.country", string="Pays")


class SmartDocument(models.Model):
    _name = "smart.student.document"
    _description = "Pièce du dossier étudiant SMART"
    _order = "required desc, document_type_id, id"

    name = fields.Char(string="Nom du document", required=True)
    application_id = fields.Many2one("smart.student.application", string="Dossier", ondelete="cascade", index=True)
    student_id = fields.Many2one(related="application_id.student_id", store=True, readonly=True)
    visa_application_id = fields.Many2one("smart.visa.application", string="Procédure visa", ondelete="cascade")
    caq_id = fields.Many2one("smart.caq", string="Dossier CAQ", ondelete="cascade")
    document_type_id = fields.Many2one("smart.document.type", string="Type de pièce")
    required = fields.Boolean(string="Obligatoire", default=True)
    state = fields.Selection([
        ("missing", "Manquant"), ("received", "Reçu"), ("validated", "Validé"), ("rejected", "À corriger")
    ], string="État", default="missing")
    file = fields.Binary(string="Fichier", attachment=True)
    filename = fields.Char()
    date_received = fields.Date()
    expiry_date = fields.Date()
    note = fields.Text()

    def action_validate(self):
        self.write({"state": "validated", "date_received": fields.Date.context_today(self)})

    def action_reject(self):
        self.write({"state": "rejected"})


class SmartStudentApplication(models.Model):
    _name = "smart.student.application"
    _description = "Dossier d'accompagnement étudiant SMART"
    _inherit = ["mail.thread", "mail.activity.mixin"]
    _order = "create_date desc"

    name = fields.Char(string="Numéro dossier", default="Nouveau", readonly=True, copy=False, tracking=True)
    student_id = fields.Many2one("smart.student", string="Étudiant", required=True, ondelete="restrict", tracking=True)
    payer_partner_id = fields.Many2one("res.partner", string="Payeur / Parent / Tuteur")
    country_id = fields.Many2one("res.country", string="Pays demandé", required=True, tracking=True)
    city = fields.Char(string="Ville")
    establishment = fields.Char(string="Établissement")
    requested_study = fields.Char(string="Formation demandée")
    study_level = fields.Selection(related="student_id.study_level", store=True, readonly=True)
    study_domain = fields.Char(related="student_id.study_domain", store=True, readonly=True)
    academic_year = fields.Char(string="Année académique")
    application_type = fields.Selection([
        ("preinscription", "Préinscription"), ("inscription", "Inscription"),
        ("both", "Préinscription + inscription")
    ], string="Type de démarche", default="preinscription", required=True)
    school_type = fields.Selection([("public", "École publique"), ("private", "École privée")], string="Type d'école")
    package_id = fields.Many2one("smart.service.package", string="Formule")
    state = fields.Selection([
        ("draft", "Brouillon"), ("registered", "Inscription"), ("in_progress", "Dossier en cours"),
        ("submitted", "Candidatures déposées"), ("preinscription", "Préinscription obtenue"),
        ("visa", "Procédure visa"), ("visa_obtained", "Visa obtenu"),
        ("completed", "Terminé"), ("cancelled", "Annulé")
    ], default="draft", tracking=True)
    registration_date = fields.Date(default=fields.Date.context_today)
    admission_date = fields.Date(string="Date de préinscription / admission")
    notes = fields.Text()

    document_ids = fields.One2many("smart.student.document", "application_id", string="Pièces")
    visa_application_ids = fields.One2many("smart.visa.application", "application_id", string="Procédures visa")
    engagement_ids = fields.One2many("smart.student.engagement", "application_id", string="Engagements")
    invoice_ids = fields.One2many("account.move", "smart_application_id", string="Factures", domain=[("move_type", "in", ["out_invoice", "out_refund"])], readonly=True)
    payment_ids = fields.One2many("account.payment", "smart_application_id", string="Paiements", readonly=True)
    document_count = fields.Integer(compute="_compute_counts")
    missing_document_count = fields.Integer(compute="_compute_counts")
    invoice_count = fields.Integer(compute="_compute_counts")
    visa_count = fields.Integer(compute="_compute_counts")
    currency_id = fields.Many2one("res.currency", default=lambda self: self.env.company.currency_id, required=True)
    total_due = fields.Monetary(compute="_compute_amounts", currency_field="currency_id", store=True)
    total_smart = fields.Monetary(compute="_compute_amounts", currency_field="currency_id", store=True)
    total_external = fields.Monetary(compute="_compute_amounts", currency_field="currency_id", store=True)
    total_invoiced = fields.Monetary(compute="_compute_amounts", currency_field="currency_id", groups="smart_student_admission.group_smart_manager")
    total_paid = fields.Monetary(compute="_compute_amounts", currency_field="currency_id", groups="smart_student_admission.group_smart_manager")
    balance_due = fields.Monetary(compute="_compute_amounts", currency_field="currency_id", groups="smart_student_admission.group_smart_manager")

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get("name", "Nouveau") == "Nouveau":
                vals["name"] = self.env["ir.sequence"].next_by_code("smart.student.application") or "Nouveau"
        return super().create(vals_list)

    @api.onchange("country_id", "application_type")
    def _onchange_package(self):
        for rec in self:
            if rec.country_id and rec.application_type:
                rec.package_id = self.env["smart.service.package"].search([
                    ("country_id", "=", rec.country_id.id),
                    ("active", "=", True),
                    "|", ("application_type", "=", rec.application_type),
                    ("application_type", "=", "both")
                ], limit=1)

    @api.depends("document_ids.state", "invoice_ids", "visa_application_ids")
    def _compute_counts(self):
        for rec in self:
            rec.document_count = len(rec.document_ids)
            rec.missing_document_count = len(rec.document_ids.filtered(lambda d: d.state in ("missing", "rejected")))
            rec.invoice_count = len(rec.invoice_ids)
            rec.visa_count = len(rec.visa_application_ids)

    @api.depends("package_id.fee_ids.amount", "package_id.fee_ids.is_external", "invoice_ids.amount_total", "payment_ids.amount", "payment_ids.state")
    def _compute_amounts(self):
        for rec in self:
            fees = rec.package_id.fee_ids if rec.package_id else self.env["smart.service.fee"]
            rec.total_due = sum(fees.mapped("amount"))
            rec.total_external = sum(fees.filtered("is_external").mapped("amount"))
            rec.total_smart = rec.total_due - rec.total_external
            invoices = rec.invoice_ids.filtered(lambda m: m.state != "cancel")
            rec.total_invoiced = sum(invoices.mapped("amount_total"))
            rec.total_paid = sum(rec.payment_ids.filtered(lambda p: p.state != "canceled").mapped("amount"))
            rec.balance_due = rec.total_invoiced - rec.total_paid

    def _get_payer_partner(self):
        self.ensure_one()
        return self.payer_partner_id or self.student_id.get_or_create_partner()

    def action_register(self):
        self.write({"state": "registered"})

    def action_start(self):
        self.write({"state": "in_progress"})

    def action_submit(self):
        self.write({"state": "submitted"})

    def action_preinscription_obtained(self):
        self.write({"state": "preinscription", "admission_date": fields.Date.context_today(self)})

    def action_create_engagement(self):
        self.ensure_one()
        engagement = self.engagement_ids[:1] or self.env["smart.student.engagement"].create({
            "application_id": self.id, "payer_partner_id": self._get_payer_partner().id
        })
        return {"type": "ir.actions.act_window", "res_model": "smart.student.engagement", "view_mode": "form", "res_id": engagement.id}

    def action_open_visa(self):
        self.ensure_one()
        if self.state in ("preinscription", "visa", "visa_obtained"):
            self.write({"state": "visa"})
        visa = self.visa_application_ids[:1] or self.env["smart.visa.application"].create({
            "application_id": self.id, "country_id": self.country_id.id
        })
        return {"type": "ir.actions.act_window", "res_model": "smart.visa.application", "view_mode": "form", "res_id": visa.id}

    def action_create_invoice(self):
        self.ensure_one()
        if not self.package_id:
            raise UserError(_("Veuillez choisir une formule d'accompagnement avant de facturer."))
        fees = self.package_id.fee_ids.filtered(lambda f: f.invoiceable and f.amount > 0)
        if not fees:
            raise UserError(_("La formule ne contient aucun frais facturable."))
        partner = self._get_payer_partner()
        journal = self.env["account.journal"].search([("type", "=", "sale"), ("company_id", "=", self.env.company.id)], limit=1)
        if not journal:
            raise UserError(_("Aucun journal de vente n'est configuré pour la société."))
        lines = []
        for fee in fees:
            if not fee.product_id:
                raise UserError(_("Le frais '%s' n'a pas de produit comptable configuré.") % fee.name)
            lines.append(Command.create({
                "product_id": fee.product_id.id, "name": fee.name, "quantity": 1,
                "price_unit": fee.amount, "smart_service_fee_id": fee.id,
            }))
        invoice = self.env["account.move"].create({
            "move_type": "out_invoice", "partner_id": partner.id, "journal_id": journal.id,
            "invoice_date": fields.Date.context_today(self), "ref": self.name,
            "smart_application_id": self.id, "smart_student_id": self.student_id.id,
            "invoice_line_ids": lines,
        })
        invoice.action_post()
        return {"type": "ir.actions.act_window", "res_model": "account.move", "view_mode": "form", "res_id": invoice.id}

    def action_register_payment(self):
        self.ensure_one()
        invoice = self.invoice_ids.filtered(lambda m: m.state == "posted" and m.payment_state != "paid")[:1]
        if not invoice:
            raise UserError(_("Aucune facture SMART ouverte à payer pour ce dossier."))
        return {
            "type": "ir.actions.act_window", "name": _("Enregistrer un paiement"),
            "res_model": "account.payment.register", "view_mode": "form", "target": "new",
            "context": {
                "active_model": "account.move", "active_ids": invoice.ids,
                "default_smart_application_id": self.id, "default_smart_student_id": self.student_id.id,
            },
        }

    def action_open_invoices(self):
        self.ensure_one()
        return {"type": "ir.actions.act_window", "res_model": "account.move", "view_mode": "list,form", "domain": [("smart_application_id", "=", self.id)]}

    def action_open_payments(self):
        self.ensure_one()
        return {"type": "ir.actions.act_window", "res_model": "account.payment", "view_mode": "list,form", "domain": [("smart_application_id", "=", self.id)]}

    def action_complete(self):
        self.write({"state": "completed"})

    def action_cancel(self):
        self.write({"state": "cancelled"})


class SmartStudentEngagement(models.Model):
    _name = "smart.student.engagement"
    _description = "Fiche d'engagement SMART"
    _inherit = ["mail.thread"]
    _order = "date desc, id desc"

    name = fields.Char(string="Numéro", default="Nouveau", readonly=True, copy=False)
    application_id = fields.Many2one("smart.student.application", required=True, ondelete="cascade")
    student_id = fields.Many2one(related="application_id.student_id", store=True, readonly=True)
    payer_partner_id = fields.Many2one("res.partner", string="Parent / Tuteur / Payeur")
    payer_name = fields.Char(string="Nom du signataire")
    payer_phone = fields.Char(string="Téléphone du signataire")
    payer_address = fields.Char(string="Adresse du signataire")
    date = fields.Date(default=fields.Date.context_today, required=True)
    signed_by = fields.Char(string="Signé par")
    state = fields.Selection([("draft", "Brouillon"), ("ready", "À signer"), ("signed", "Signé"), ("cancelled", "Annulé")], default="draft", tracking=True)
    amount_dossier = fields.Monetary(compute="_compute_amounts", currency_field="currency_id", store=True)
    amount_honoraires = fields.Monetary(compute="_compute_amounts", currency_field="currency_id", store=True)
    total_amount = fields.Monetary(compute="_compute_amounts", currency_field="currency_id", store=True)
    currency_id = fields.Many2one(related="application_id.currency_id", store=True, readonly=True)
    legal_text = fields.Html(string="Texte d'engagement", default=lambda self: _(
        "<p>Le client sollicite l'assistance de l'Agence SMART Assistance Consulting &amp; Trading pour l'accompagnement dans les démarches de préinscription ou d'inscription à l'étranger.</p>"
        "<p>Les frais applicables sont ceux de la formule sélectionnée. Les frais externes peuvent rester à la charge de l'étudiant.</p>"
    ))

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get("name", "Nouveau") == "Nouveau":
                vals["name"] = self.env["ir.sequence"].next_by_code("smart.student.engagement") or "Nouveau"
        return super().create(vals_list)

    @api.depends("application_id.package_id.fee_ids.amount", "application_id.package_id.fee_ids.fee_type")
    def _compute_amounts(self):
        for rec in self:
            fees = rec.application_id.package_id.fee_ids
            rec.amount_dossier = sum(fees.filtered(lambda f: f.fee_type == "dossier").mapped("amount"))
            rec.amount_honoraires = sum(fees.filtered(lambda f: f.fee_type == "honoraires").mapped("amount"))
            rec.total_amount = sum(fees.mapped("amount"))

    def action_ready(self):
        self.write({"state": "ready"})

    def action_sign(self):
        self.write({"state": "signed", "signed_by": self.payer_name or self.student_id.name})

    def action_cancel(self):
        self.write({"state": "cancelled"})

    def action_print(self):
        return self.env.ref("smart_student_admission.action_report_smart_engagement").report_action(self)


class SmartVisaStage(models.Model):
    _name = "smart.visa.stage"
    _description = "Étape de procédure visa"
    _order = "country_id, sequence, id"

    name = fields.Char(required=True)
    code = fields.Char(required=True)
    country_id = fields.Many2one("res.country", string="Pays")
    sequence = fields.Integer(default=10)
    stage_kind = fields.Selection([
        ("preparation", "Préparation"), ("caq", "CAQ"), ("application", "Demande"),
        ("biometrics", "Biométrie / rendez-vous"), ("processing", "Traitement"), ("decision", "Décision")
    ], default="preparation", required=True)
    required = fields.Boolean(default=True)
    active = fields.Boolean(default=True)

    _sql_constraints = [("visa_stage_code_country_uniq", "unique(code, country_id)", "Le code d'étape doit être unique pour un pays.")]


class SmartVisaApplication(models.Model):
    _name = "smart.visa.application"
    _description = "Procédure Visa / Immigration SMART"
    _inherit = ["mail.thread", "mail.activity.mixin"]
    _order = "date_start desc, id desc"

    name = fields.Char(string="Numéro", default="Nouveau", readonly=True, copy=False)
    application_id = fields.Many2one("smart.student.application", required=True, ondelete="cascade")
    student_id = fields.Many2one(related="application_id.student_id", store=True, readonly=True)
    country_id = fields.Many2one("res.country", related="application_id.country_id", store=True, readonly=True)
    is_canada = fields.Boolean(compute="_compute_is_canada")
    visa_type = fields.Selection([("study", "Visa / permis d'études"), ("student", "Visa étudiant"), ("other", "Autre")], default="study")
    state = fields.Selection([
        ("draft", "À préparer"), ("documents", "Documents en préparation"), ("complete", "Dossier complet"),
        ("submitted", "Demande déposée"), ("appointment", "Biométrie / rendez-vous"),
        ("processing", "En traitement"), ("decision", "Décision"), ("obtained", "Visa / permis obtenu"),
        ("refused", "Refusé"), ("cancelled", "Annulé")
    ], default="draft", tracking=True)
    date_start = fields.Date(string="Début de procédure", default=fields.Date.context_today)
    date_submission = fields.Date()
    date_decision = fields.Date()
    result_reference = fields.Char(string="Référence / numéro de décision")
    note = fields.Text()
    step_ids = fields.One2many("smart.visa.application.step", "visa_application_id", string="Étapes")
    caq_ids = fields.One2many("smart.caq", "visa_application_id", string="Demandes CAQ")
    document_ids = fields.One2many("smart.student.document", "visa_application_id", string="Pièces")
    step_count = fields.Integer(compute="_compute_counts")
    missing_step_count = fields.Integer(compute="_compute_counts")

    @api.depends("country_id")
    def _compute_is_canada(self):
        for rec in self:
            rec.is_canada = rec.country_id.code == "CA"

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get("name", "Nouveau") == "Nouveau":
                vals["name"] = self.env["ir.sequence"].next_by_code("smart.visa.application") or "Nouveau"
        records = super().create(vals_list)
        records.action_initialize_steps()
        return records

    @api.depends("step_ids.state")
    def _compute_counts(self):
        for rec in self:
            rec.step_count = len(rec.step_ids)
            rec.missing_step_count = len(rec.step_ids.filtered(lambda s: s.required and s.state not in ("done", "not_applicable")))

    def action_initialize_steps(self):
        for rec in self:
            if rec.step_ids:
                continue
            stages = self.env["smart.visa.stage"].search([
                "|", ("country_id", "=", rec.country_id.id), ("country_id", "=", False), ("active", "=", True)
            ], order="country_id desc, sequence, id")
            seen = set()
            for stage in stages:
                if stage.code in seen:
                    continue
                seen.add(stage.code)
                self.env["smart.visa.application.step"].create({
                    "visa_application_id": rec.id, "stage_id": stage.id,
                    "name": stage.name, "sequence": stage.sequence, "required": stage.required,
                })
        return True

    def action_create_caq(self):
        self.ensure_one()
        if not self.is_canada:
            raise UserError(_("Le CAQ est réservé aux dossiers Canada."))
        caq = self.caq_ids[:1] or self.env["smart.caq"].create({
            "visa_application_id": self.id, "application_id": self.application_id.id,
            "institution": self.application_id.establishment, "program": self.application_id.requested_study,
        })
        return {"type": "ir.actions.act_window", "res_model": "smart.caq", "view_mode": "form", "res_id": caq.id}

    def action_start(self):
        self.write({"state": "documents"})

    def action_mark_complete(self):
        self.write({"state": "complete"})

    def action_submit(self):
        self.write({"state": "submitted", "date_submission": fields.Date.context_today(self)})

    def action_appointment(self):
        self.write({"state": "appointment"})

    def action_processing(self):
        self.write({"state": "processing"})

    def action_decision(self):
        self.write({"state": "decision", "date_decision": fields.Date.context_today(self)})

    def action_obtained(self):
        self.write({"state": "obtained"})
        self.application_id.write({"state": "visa_obtained"})

    def action_refused(self):
        self.write({"state": "refused"})


class SmartVisaApplicationStep(models.Model):
    _name = "smart.visa.application.step"
    _description = "Étape d'une procédure visa"
    _order = "sequence, id"

    visa_application_id = fields.Many2one("smart.visa.application", required=True, ondelete="cascade")
    stage_id = fields.Many2one("smart.visa.stage", string="Modèle d'étape")
    name = fields.Char(required=True)
    sequence = fields.Integer(default=10)
    required = fields.Boolean(default=True)
    state = fields.Selection([("todo", "À faire"), ("in_progress", "En cours"), ("done", "Terminé"), ("not_applicable", "Non applicable")], default="todo")
    date_start = fields.Date()
    date_done = fields.Date()
    reference = fields.Char()
    note = fields.Text()

    def action_start(self):
        self.write({"state": "in_progress", "date_start": fields.Date.context_today(self)})

    def action_done(self):
        self.write({"state": "done", "date_done": fields.Date.context_today(self)})


class SmartCaq(models.Model):
    _name = "smart.caq"
    _description = "Demande de CAQ Canada"
    _inherit = ["mail.thread"]

    name = fields.Char(string="Numéro CAQ", default="Nouveau", readonly=True, copy=False)
    visa_application_id = fields.Many2one("smart.visa.application", required=True, ondelete="cascade", index=True)
    application_id = fields.Many2one("smart.student.application", required=True, ondelete="cascade")
    student_id = fields.Many2one(related="application_id.student_id", store=True, readonly=True)
    institution = fields.Char(string="Établissement")
    program = fields.Char(string="Programme")
    level = fields.Selection(related="application_id.study_level", readonly=True)
    request_number = fields.Char(string="Numéro de demande")
    submission_date = fields.Date()
    decision_date = fields.Date()
    expiry_date = fields.Date()
    state = fields.Selection([("draft", "À préparer"), ("submitted", "Soumis"), ("processing", "En traitement"), ("obtained", "CAQ obtenu"), ("refused", "Refusé")], default="draft", tracking=True)
    proof_file = fields.Binary(string="Document CAQ", attachment=True)
    proof_filename = fields.Char()
    note = fields.Text()

    _sql_constraints = [("caq_one_per_visa", "unique(visa_application_id)", "Une seule demande CAQ est autorisée par procédure visa.")]

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get("name", "Nouveau") == "Nouveau":
                vals["name"] = self.env["ir.sequence"].next_by_code("smart.caq") or "Nouveau"
        return super().create(vals_list)

    def action_submit(self):
        self.write({"state": "submitted", "submission_date": fields.Date.context_today(self)})

    def action_processing(self):
        self.write({"state": "processing"})

    def action_obtained(self):
        self.write({"state": "obtained", "decision_date": fields.Date.context_today(self)})

    def action_refused(self):
        self.write({"state": "refused", "decision_date": fields.Date.context_today(self)})


class AccountMove(models.Model):
    _inherit = "account.move"

    smart_application_id = fields.Many2one("smart.student.application", string="Dossier SMART", copy=False, index=True)
    smart_student_id = fields.Many2one("smart.student", string="Étudiant SMART", copy=False, index=True)


class AccountMoveLine(models.Model):
    _inherit = "account.move.line"

    smart_service_fee_id = fields.Many2one("smart.service.fee", string="Frais SMART", copy=False, index=True)


class AccountPayment(models.Model):
    _inherit = "account.payment"

    smart_application_id = fields.Many2one("smart.student.application", string="Dossier SMART", copy=False, index=True)
    smart_student_id = fields.Many2one("smart.student", string="Étudiant SMART", copy=False, index=True)


class AccountPaymentRegister(models.TransientModel):
    _inherit = "account.payment.register"

    smart_application_id = fields.Many2one("smart.student.application", string="Dossier SMART")
    smart_student_id = fields.Many2one("smart.student", string="Étudiant SMART")

    def _create_payment_vals_from_wizard(self, batch_result):
        vals = super()._create_payment_vals_from_wizard(batch_result)
        vals.update({"smart_application_id": self.smart_application_id.id, "smart_student_id": self.smart_student_id.id})
        return vals

    def _create_payment_vals_from_batch(self, batch_result):
        vals = super()._create_payment_vals_from_batch(batch_result)
        vals.update({"smart_application_id": self.smart_application_id.id, "smart_student_id": self.smart_student_id.id})
        return vals
