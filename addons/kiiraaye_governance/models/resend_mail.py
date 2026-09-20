import os

from odoo import api, models


class ResendMailServer(models.Model):
    _inherit = "ir.mail_server"

    @api.model
    def _get_resend_configuration(self):
        api_key = os.getenv("RESEND_SMTP_PASSWORD") or os.getenv("RESEND_API_KEY")
        sender = os.getenv("RESEND_FROM_EMAIL")
        if not api_key or not sender:
            return None

        try:
            port = int(os.getenv("RESEND_SMTP_PORT", "465"))
        except (TypeError, ValueError):
            port = 465

        return {
            "name": "Resend SMTP",
            "smtp_host": os.getenv("RESEND_SMTP_HOST", "smtp.resend.com"),
            "smtp_port": port,
            "smtp_authentication": "login",
            "smtp_user": os.getenv("RESEND_SMTP_USER", "resend"),
            "smtp_pass": api_key,
            "smtp_encryption": "ssl",
            "from_filter": sender,
            "sequence": 1,
            "active": True,
        }

    @api.model
    def _get_or_create_resend_server(self):
        values = self._get_resend_configuration()
        if not values:
            return self.browse()

        server = self.sudo().search([("name", "=", "Resend SMTP")], limit=1)
        if server:
            server.sudo().write(values)
            return server

        return self.sudo().create(values)

    @api.model
    def _find_mail_server(self, email_from, mail_servers=None):
        server = self._get_or_create_resend_server()
        if server:
            # Resend's onboarding sender is the only sender available before
            # a custom domain is verified. Force it for default outgoing mail.
            sender = os.getenv("RESEND_FROM_EMAIL", email_from)
            return server, sender

        return super()._find_mail_server(email_from, mail_servers)


class ResendMailMail(models.Model):
    _inherit = "mail.mail"

    def _prepare_outgoing_list(self, mail_server=False, doc_to_followers=None):
        outgoing = super()._prepare_outgoing_list(
            mail_server=mail_server,
            doc_to_followers=doc_to_followers,
        )

        sender = os.getenv("RESEND_FROM_EMAIL")
        if not sender:
            return outgoing

        for values in outgoing:
            values["email_from"] = sender
            headers = values.get("headers") or {}
            headers["Return-Path"] = sender
            values["headers"] = headers

        return outgoing
