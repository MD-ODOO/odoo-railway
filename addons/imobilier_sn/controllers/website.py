# -*- coding: utf-8 -*-
import re
from urllib.parse import quote_plus

from odoo import http
from odoo.http import request


class ImobilierSNWebsite(http.Controller):

    @staticmethod
    def _whatsapp_number(phone):
        if not phone:
            return False
        digits = re.sub(r"\D", "", phone)
        if len(digits) == 9 and digits.startswith(("30", "33", "70", "75", "76", "77", "78")):
            digits = "221" + digits
        return digits or False

    @staticmethod
    def _contact_data(property_rec):
        partner = property_rec.owner_id
        phone = partner.phone or partner.mobile or False
        labels = dict(property_rec._fields["property_type"].selection)
        return {
            "phone": phone,
            "email": partner.email or False,
            "whatsapp": ImobilierSNWebsite._whatsapp_number(phone),
            "name": partner.display_name,
            "type_label": labels.get(property_rec.property_type, ""),
            "whatsapp_message": quote_plus(
                "Bonjour, je suis intéressé par le produit %s" % property_rec.reference
            ),
            "email_subject": quote_plus(
                "Demande concernant %s" % property_rec.reference
            ),
        }

    @http.route(
        "/immobilier",
        type="http",
        auth="public",
        website=True,
        sitemap=True,
    )
    def immobilier_list(self, **kwargs):
        properties = request.env["imobilier.sn.property"].sudo().search(
            [
                ("active", "=", True),
                ("website_published", "=", True),
                ("status", "!=", "unavailable"),
            ],
            order="id desc",
        )
        values = {
            "properties": properties,
            "contact_data": {
                prop.id: self._contact_data(prop)
                for prop in properties
            },
        }
        return request.render("imobilier_sn.website_property_list", values)

    @http.route(
        "/immobilier/<int:property_id>",
        type="http",
        auth="public",
        website=True,
        sitemap=True,
    )
    def immobilier_detail(self, property_id, **kwargs):
        property_rec = request.env["imobilier.sn.property"].sudo().browse(property_id)
        if not property_rec.exists() or not property_rec.active or not property_rec.website_published:
            return request.not_found()

        values = {
            "property": property_rec,
            "contact": self._contact_data(property_rec),
        }
        return request.render("imobilier_sn.website_property_detail", values)
