from datetime import date

from odoo import api, fields, models


class ImobilierSNDashboard(models.Model):
    _auto = False
    _name = "imobilier.sn.dashboard"
    _description = "Tableau de bord Immobilier SN"

    @api.model
    def _year_dates(self, year):
        try:
            year = int(year)
        except (TypeError, ValueError):
            year = fields.Date.context_today(self).year
        return date(year, 1, 1), date(year + 1, 1, 1), year

    @api.model
    def get_filter_options(self):
        Property = self.env["imobilier.sn.property"]
        locations = Property.search(
            [("location", "!=", False)],
            order="location",
            limit=2000,
        ).mapped("location")
        locations = sorted(set(locations), key=lambda value: value.lower())
        current_year = fields.Date.context_today(self).year
        return {
            "locations": locations,
            "years": list(range(current_year - 5, current_year + 2)),
            "default_year": current_year,
        }

    @api.model
    def get_dashboard_data(self, year=None, location=None):
        date_from, date_to, year = self._year_dates(year)
        location = (location or "").strip()

        Property = self.env["imobilier.sn.property"]
        Contract = self.env["imobilier.sn.contract"]
        Payment = self.env["imobilier.sn.contract.payment"]

        property_domain = [
            ("create_date", ">=", fields.Datetime.to_string(date_from)),
            ("create_date", "<", fields.Datetime.to_string(date_to)),
        ]
        if location:
            property_domain.append(("location", "=", location))

        def count(property_type):
            return Property.search_count(
                property_domain + [("property_type", "=", property_type)]
            )

        rental_domain = [
            ("contract_type", "=", "rent"),
            ("date_start", ">=", date_from),
            ("date_start", "<", date_to),
        ]
        if location:
            rental_domain.append(("property_id.location", "=", location))
        rental_contracts = Contract.search(rental_domain)

        today = fields.Date.context_today(self)
        month_start = today.replace(day=1)
        if today.month == 12:
            month_end = today.replace(year=today.year + 1, month=1, day=1)
        else:
            month_end = today.replace(month=today.month + 1, day=1)

        rent_domain = [
            ("contract_id.contract_type", "=", "rent"),
            ("due_date", ">=", month_start),
            ("due_date", "<", month_end),
            ("contract_id.state", "not in", ["cancelled"]),
        ]
        if location:
            rent_domain.append(("contract_id.property_id.location", "=", location))

        monthly_payments = Payment.search(rent_domain)
        paid_payments = monthly_payments.filtered(lambda p: p.state == "paid")
        unpaid_payments = monthly_payments - paid_payments

        total_monthly_due = sum(monthly_payments.mapped("amount"))
        total_monthly_paid = sum(paid_payments.mapped("amount"))

        return {
            "year": year,
            "location": location,
            "location_label": location or "Tous les lieux",
            "today": fields.Date.to_string(today),
            "month_label": month_start.strftime("%m/%Y"),
            "currency_symbol": self.env.company.currency_id.symbol or self.env.company.currency_id.name or "FCFA",
            "kpi": {
                "properties": Property.search_count(property_domain),
                "apartments": count("apartment"),
                "houses": count("house"),
                "shops": count("shop"),
                "lands": count("land"),
                "rentals": len(rental_contracts),
                "rentals_paid_month": len(paid_payments),
                "rentals_due_month": len(monthly_payments),
                "rentals_unpaid_month": len(unpaid_payments),
                "rent_paid_amount_month": total_monthly_paid,
                "rent_due_amount_month": total_monthly_due,
                "rent_collection_rate": (
                    total_monthly_paid / total_monthly_due * 100
                    if total_monthly_due
                    else 0
                ),
            },
            "current_rents": [
                {
                    "id": p.id,
                    "due_date": fields.Date.to_string(p.due_date),
                    "tenant": p.contract_id.customer_id.display_name,
                    "property": p.contract_id.property_id.display_name,
                    "reference": p.contract_id.property_id.reference,
                    "location": p.contract_id.property_id.location,
                    "amount": p.amount,
                    "state": p.state,
                }
                for p in monthly_payments.sorted(
                    key=lambda record: (record.due_date, record.id)
                )
            ],
        }
