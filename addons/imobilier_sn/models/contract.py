from dateutil.relativedelta import relativedelta

from odoo import api, fields, models, _
from odoo.exceptions import UserError, ValidationError


class ImobilierSNContract(models.Model):
    _name = "imobilier.sn.contract"
    _description = "Contrat immobilier"
    _inherit = ["mail.thread", "mail.activity.mixin"]
    _order = "id desc"

    name = fields.Char(
        string="Référence contrat",
        default=lambda self: self.env["ir.sequence"].next_by_code("imobilier.sn.contract") or "Nouveau",
        readonly=True,
        copy=False,
        tracking=True,
    )
    contract_type = fields.Selection(
        [("rent", "Location"), ("sale", "Achat / Vente")],
        string="Type de contrat",
        required=True,
        tracking=True,
    )
    property_id = fields.Many2one(
        "imobilier.sn.property",
        string="Produit",
        required=True,
        tracking=True,
        ondelete="restrict",
    )
    customer_id = fields.Many2one(
        "res.partner",
        string="Client / Locataire / Acheteur",
        required=True,
        tracking=True,
        ondelete="restrict",
    )
    broker_id = fields.Many2one(
        "res.partner",
        string="Courtier",
        domain=[("is_imobilier_broker", "=", True)],
        ondelete="restrict",
    )
    currency_id = fields.Many2one(
        related="property_id.currency_id",
        string="Devise",
        readonly=True,
    )

    date_start = fields.Date(
        string="Date de début",
        default=fields.Date.context_today,
        required=True,
    )
    date_end = fields.Date(string="Date de fin")

    # Location
    monthly_rent = fields.Monetary(string="Loyer mensuel", currency_field="currency_id")
    security_deposit = fields.Monetary(string="Caution", currency_field="currency_id")
    advance_months = fields.Float(string="Nombre de mois d'avance")
    payment_mode_rent = fields.Selection(
        [
            ("monthly", "Mensuel"),
            ("quarterly", "Trimestriel"),
            ("custom", "Autre"),
        ],
        string="Paiement du loyer",
        default="monthly",
    )

    # Vente
    sale_price = fields.Monetary(string="Prix de vente", currency_field="currency_id")
    down_payment = fields.Monetary(string="Acompte", currency_field="currency_id")
    number_of_installments = fields.Integer(string="Nombre d'échéances", default=1)
    payment_frequency_months = fields.Selection(
        [
            ("1", "Chaque mois"),
            ("3", "Chaque trimestre"),
            ("6", "Tous les 6 mois"),
            ("12", "Annuel"),
        ],
        string="Périodicité des échéances",
        default="1",
    )
    payment_mode_sale = fields.Char(
        string="Modalité de paiement",
        help="Permet de préciser une modalité particulière convenue avec l'acheteur.",
    )

    payment_line_ids = fields.One2many(
        "imobilier.sn.contract.payment",
        "contract_id",
        string="Échéancier",
        copy=False,
    )
    inspection_ids = fields.One2many(
        "imobilier.sn.inspection",
        "contract_id",
        string="États des lieux",
        copy=False,
    )

    contract_file = fields.Binary(string="Contrat signé")
    contract_filename = fields.Char(string="Nom du contrat")
    notes = fields.Text(string="Notes")

    state = fields.Selection(
        [
            ("draft", "Brouillon"),
            ("confirmed", "Confirmé"),
            ("active", "Actif"),
            ("closed", "Clôturé"),
            ("cancelled", "Annulé"),
        ],
        string="État",
        default="draft",
        tracking=True,
    )

    @api.onchange("property_id", "contract_type")
    def _onchange_property(self):
        for rec in self:
            if not rec.property_id:
                continue
            if rec.contract_type == "rent":
                rec.monthly_rent = rec.property_id.rental_price or rec.property_id.price
                rec.security_deposit = (
                    rec.property_id.security_deposit
                    or rec.property_id.shop_deposit
                    or 0
                )
                rec.advance_months = rec.property_id.rental_advance_count or 0
            elif rec.contract_type == "sale":
                rec.sale_price = rec.property_id.price

    @api.constrains("contract_type", "number_of_installments", "down_payment", "sale_price")
    def _check_sale_values(self):
        for rec in self:
            if rec.contract_type == "sale":
                if rec.sale_price <= 0:
                    raise ValidationError(_("Le prix de vente doit être supérieur à zéro."))
                if rec.number_of_installments < 1:
                    raise ValidationError(_("Le nombre d'échéances doit être supérieur ou égal à 1."))
                if rec.down_payment < 0 or rec.down_payment > rec.sale_price:
                    raise ValidationError(_("L'acompte doit être compris entre 0 et le prix de vente."))

    def action_generate_schedule(self):
        for rec in self:
            rec.payment_line_ids.filtered(lambda l: not l.invoice_id).unlink()
            if rec.contract_type == "rent":
                rec._generate_rent_schedule()
            else:
                rec._generate_sale_schedule()
        return True

    def _generate_rent_schedule(self):
        self.ensure_one()
        if not self.monthly_rent or self.monthly_rent <= 0:
            raise UserError(_("Veuillez renseigner le loyer mensuel."))
        start = self.date_start
        if not start:
            raise UserError(_("Veuillez renseigner la date de début."))
        stop = self.date_end or (start + relativedelta(months=11))
        # Caution
        if self.security_deposit:
            self.env["imobilier.sn.contract.payment"].create({
                "contract_id": self.id,
                "due_date": start,
                "description": _("Caution"),
                "payment_kind": "deposit",
                "amount": self.security_deposit,
            })
        # Avance de loyers
        if self.advance_months:
            advance_amount = self.monthly_rent * self.advance_months
            self.env["imobilier.sn.contract.payment"].create({
                "contract_id": self.id,
                "due_date": start,
                "description": _("Avance de loyer (%s mois)") % self.advance_months,
                "payment_kind": "advance",
                "amount": advance_amount,
            })
        months = 3 if self.payment_mode_rent == "quarterly" else 1
        due = start + relativedelta(months=months)
        while due <= stop:
            amount = self.monthly_rent * months
            self.env["imobilier.sn.contract.payment"].create({
                "contract_id": self.id,
                "due_date": due,
                "description": _("Loyer"),
                "payment_kind": "rent",
                "amount": amount,
            })
            due += relativedelta(months=months)

    def _generate_sale_schedule(self):
        self.ensure_one()
        remaining = self.sale_price - self.down_payment
        if self.down_payment:
            self.env["imobilier.sn.contract.payment"].create({
                "contract_id": self.id,
                "due_date": self.date_start,
                "description": _("Acompte"),
                "payment_kind": "down_payment",
                "amount": self.down_payment,
            })
        installment = remaining / self.number_of_installments
        step = int(self.payment_frequency_months or "1")
        for index in range(self.number_of_installments):
            due = self.date_start + relativedelta(months=step * (index + 1))
            self.env["imobilier.sn.contract.payment"].create({
                "contract_id": self.id,
                "due_date": due,
                "description": _("Échéance %s/%s") % (index + 1, self.number_of_installments),
                "payment_kind": "sale_installment",
                "amount": installment,
            })


    @api.model
    def _cron_generate_current_month_rents(self):
        today = fields.Date.context_today(self)
        month_start = today.replace(day=1)
        if today.month == 12:
            next_month = today.replace(year=today.year + 1, month=1, day=1)
        else:
            next_month = today.replace(month=today.month + 1, day=1)

        contracts = self.search([
            ("contract_type", "=", "rent"),
            ("state", "in", ["confirmed", "active"]),
            ("payment_mode_rent", "=", "monthly"),
            ("date_start", "<", next_month),
            "|",
            ("date_end", "=", False),
            ("date_end", ">=", month_start),
        ])
        Payment = self.env["imobilier.sn.contract.payment"]
        created = 0
        for contract in contracts:
            existing = Payment.search_count([
                ("contract_id", "=", contract.id),
                ("payment_kind", "=", "rent"),
                ("due_date", ">=", month_start),
                ("due_date", "<", next_month),
            ])
            if not existing and contract.monthly_rent > 0:
                Payment.create({
                    "contract_id": contract.id,
                    "due_date": month_start,
                    "description": _("Loyer"),
                    "amount": contract.monthly_rent,
                })
                created += 1
        return created

    def action_confirm(self):
        for rec in self:
            if not rec.payment_line_ids:
                rec.action_generate_schedule()
            if rec.contract_type == "rent":
                rec.property_id.status = "rented"
                rec.customer_id.is_imobilier_tenant = True
                profile = self.env["imobilier.sn.tenant.profile"].search(
                    [("partner_id", "=", rec.customer_id.id)], limit=1
                )
                if not profile:
                    self.env["imobilier.sn.tenant.profile"].create({"partner_id": rec.customer_id.id})
            else:
                rec.property_id.status = "reserved"
            rec.state = "confirmed"
        return True

    def action_activate(self):
        self.write({"state": "active"})
        return True

    def action_close(self):
        for rec in self:
            rec.state = "closed"
            if rec.contract_type == "sale":
                rec.property_id.status = "sold"
        return True

    def action_cancel(self):
        for rec in self:
            rec.state = "cancelled"
        return True

    def action_create_all_invoices(self):
        for line in self.payment_line_ids.filtered(lambda l: not l.invoice_id and l.amount > 0):
            line.action_create_invoice()
        return True


class ImobilierSNContractPayment(models.Model):
    _name = "imobilier.sn.contract.payment"
    _description = "Échéance de contrat"
    _order = "due_date, id"

    contract_id = fields.Many2one(
        "imobilier.sn.contract",
        required=True,
        ondelete="cascade",
    )
    property_id = fields.Many2one(
        "imobilier.sn.property",
        related="contract_id.property_id",
        string="Produit",
        store=True,
        readonly=True,
    )
    customer_id = fields.Many2one(
        "res.partner",
        related="contract_id.customer_id",
        string="Client",
        store=True,
        readonly=True,
    )
    payment_kind = fields.Selection(
        [
            ("rent", "Loyer"),
            ("deposit", "Caution"),
            ("advance", "Avance"),
            ("down_payment", "Acompte"),
            ("sale_installment", "Échéance de vente"),
        ],
        string="Type d'échéance",
        required=True,
        default="rent",
    )
    due_date = fields.Date(string="Échéance", required=True)
    description = fields.Char(string="Libellé", required=True)
    amount = fields.Monetary(
        string="Montant",
        currency_field="currency_id",
        required=True,
    )
    currency_id = fields.Many2one(
        related="contract_id.currency_id",
        string="Devise",
        readonly=True,
    )
    invoice_id = fields.Many2one(
        "account.move",
        string="Facture",
        readonly=True,
        copy=False,
    )
    state = fields.Selection(
        [
            ("pending", "À encaisser"),
            ("invoiced", "Facturé"),
            ("in_payment", "En paiement"),
            ("paid", "Payé"),
            ("cancelled", "Annulé"),
        ],
        string="État",
        compute="_compute_state",
        store=True,
    )

    @api.depends("invoice_id", "invoice_id.state", "invoice_id.payment_state")
    def _compute_state(self):
        for rec in self:
            move = rec.invoice_id
            if not move:
                rec.state = "pending"
            elif move.state == "cancel":
                rec.state = "cancelled"
            elif move.payment_state == "paid":
                rec.state = "paid"
            elif move.payment_state == "in_payment":
                rec.state = "in_payment"
            else:
                rec.state = "invoiced"

    def action_create_invoice(self):
        self.ensure_one()
        if self.invoice_id:
            return self.action_open_invoice()
        journal = self.env["account.journal"].search(
            [("type", "=", "sale"), ("company_id", "=", self.env.company.id)],
            limit=1,
        )
        if not journal:
            raise UserError(_("Aucun journal de vente n'est configuré."))
        income_account = self.env["account.account"].search(
            [
                ("company_ids", "in", self.env.company.id),
                ("account_type", "in", ["income", "income_other"]),
            ],
            limit=1,
        )
        if not income_account:
            raise UserError(_("Aucun compte de produit n'est disponible pour créer la facture."))
        move = self.env["account.move"].create({
            "move_type": "out_invoice",
            "partner_id": self.contract_id.customer_id.id,
            "journal_id": journal.id,
            "invoice_date": fields.Date.context_today(self),
            "invoice_line_ids": [(0, 0, {
                "name": self.description or self.contract_id.name,
                "quantity": 1,
                "price_unit": self.amount,
                "account_id": income_account.id,
            })],
        })
        self.invoice_id = move.id
        return self.action_open_invoice()

    def action_open_invoice(self):
        self.ensure_one()
        if not self.invoice_id:
            return self.action_create_invoice()
        return {
            "type": "ir.actions.act_window",
            "name": _("Facture"),
            "res_model": "account.move",
            "view_mode": "form",
            "res_id": self.invoice_id.id,
            "target": "current",
        }

    @api.model
    def action_current_month_payments(self, paid=False, location=False):
        today = fields.Date.context_today(self)
        start = today.replace(day=1)
        if today.month == 12:
            end = today.replace(year=today.year + 1, month=1, day=1)
        else:
            end = today.replace(month=today.month + 1, day=1)

        domain = [
            ("contract_id.contract_type", "=", "rent"),
            ("payment_kind", "=", "rent"),
            ("due_date", ">=", start),
            ("due_date", "<", end),
        ]
        if location:
            domain.append(("property_id.location", "=", location))
        if paid:
            domain.append(("state", "=", "paid"))
            name = _("Locations payées du mois")
        else:
            domain.append(("state", "!=", "paid"))
            name = _("Locations à payer du mois")

        return {
            "type": "ir.actions.act_window",
            "name": name,
            "res_model": "imobilier.sn.contract.payment",
            "view_mode": "list,form",
            "domain": domain,
        }

    def action_open_contract(self):
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "name": _("Contrat"),
            "res_model": "imobilier.sn.contract",
            "view_mode": "form",
            "res_id": self.contract_id.id,
            "target": "current",
        }
