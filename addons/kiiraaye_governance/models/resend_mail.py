import base64
import json
import logging
import os
import urllib.error
import urllib.request

from odoo import api, models, tools

from odoo.addons.base.models.ir_mail_server import MailDeliveryException


_logger = logging.getLogger(__name__)


class ResendMailMail(models.Model):
    _inherit = "mail.mail"

    @api.model
    def _resend_configuration(self):
        api_key = os.getenv("RESEND_SMTP_PASSWORD") or os.getenv("RESEND_API_KEY")
        sender = os.getenv("RESEND_FROM_EMAIL")
        if not api_key or not sender:
            return None
        return api_key, sender

    def _resend_recipients(self, mail):
        recipients = []
        for email in tools.mail.email_normalize_all(mail.email_to or ""):
            if email and email not in recipients:
                recipients.append(email)

        for partner in mail.recipient_ids:
            for email in tools.mail.email_normalize_all(partner.email or ""):
                if email and email not in recipients:
                    recipients.append(email)

        return recipients

    def _resend_cc(self, mail):
        cc = []
        for email in tools.mail.email_normalize_all(mail.email_cc or ""):
            if email and email not in cc:
                cc.append(email)
        return cc

    def _resend_reply_to(self, mail):
        reply_to = []
        for email in tools.mail.email_normalize_all(mail.reply_to or ""):
            if email and email not in reply_to:
                reply_to.append(email)
        return reply_to

    def _resend_payload(self):
        self.ensure_one()
        configuration = self._resend_configuration()
        if not configuration:
            return None

        api_key, sender = configuration
        recipients = self._resend_recipients(self)
        if not recipients:
            raise MailDeliveryException("Aucun destinataire valide pour l'e-mail.")

        payload = {
            "from": sender,
            "to": recipients,
            "subject": self.subject or "",
            "html": self.body_html or "",
            "text": tools.html2plaintext(self.body_html or ""),
        }

        cc = self._resend_cc(self)
        if cc:
            payload["cc"] = cc

        reply_to = self._resend_reply_to(self)
        if reply_to:
            payload["reply_to"] = reply_to

        attachments = []
        for attachment in self.attachment_ids.sudo():
            raw = attachment.raw
            if not raw:
                continue
            attachments.append({
                "filename": attachment.name or "attachment",
                "content": base64.b64encode(bytes(raw)).decode("ascii"),
            })
        if attachments:
            payload["attachments"] = attachments

        return api_key, payload, recipients

    def _send_via_resend(self):
        self.ensure_one()
        prepared = self._resend_payload()
        if not prepared:
            return None

        api_key, payload, recipients = prepared
        body = json.dumps(payload).encode("utf-8")
        request = urllib.request.Request(
            "https://api.resend.com/emails",
            data=body,
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
                "User-Agent": "Odoo/19 Resend Integration",
            },
            method="POST",
        )

        try:
            with urllib.request.urlopen(request, timeout=30) as response:
                response_body = response.read().decode("utf-8")
        except urllib.error.HTTPError as exc:
            response_body = exc.read().decode("utf-8", errors="replace")
            raise MailDeliveryException(
                f"Resend API a refusé l'e-mail (HTTP {exc.code}): {response_body[:1000]}"
            ) from exc
        except urllib.error.URLError as exc:
            raise MailDeliveryException(
                f"Connexion HTTPS vers Resend impossible: {exc.reason}"
            ) from exc
        except Exception as exc:
            raise MailDeliveryException(
                f"Erreur lors de l'appel à l'API Resend: {exc}"
            ) from exc

        try:
            result = json.loads(response_body or "{}")
        except json.JSONDecodeError as exc:
            raise MailDeliveryException(
                f"Réponse Resend invalide: {response_body[:1000]}"
            ) from exc

        resend_id = result.get("id")
        if not resend_id:
            raise MailDeliveryException(
                f"Resend n'a pas retourné d'identifiant d'e-mail: {response_body[:1000]}"
            )

        _logger.info(
            "Mail (mail.mail) ID %r successfully sent via Resend API as %s",
            self.id,
            resend_id,
        )
        return resend_id, recipients

    def send(self, auto_commit=False, raise_exception=False, post_send_callback=None):
        configuration = self._resend_configuration()
        if not configuration:
            return super().send(
                auto_commit=auto_commit,
                raise_exception=raise_exception,
                post_send_callback=post_send_callback,
            )

        for mail in self:
            if mail.state != "outgoing":
                continue

            success_emails = []
            success_pids = []
            try:
                result = mail._send_via_resend()
                if not result:
                    continue

                resend_id, success_emails = result
                success_pids = list(mail.recipient_ids)

                mail.write({
                    "state": "sent",
                    "message_id": resend_id,
                    "failure_type": False,
                    "failure_reason": False,
                })
                mail._postprocess_sent_message(
                    success_pids=success_pids,
                    success_emails=success_emails,
                    failure_reason=False,
                    failure_type=None,
                )

                if post_send_callback:
                    post_send_callback([mail.id])
                if auto_commit:
                    self.env.cr.commit()

            except Exception as exc:
                failure_reason = tools.exception_to_unicode(exc)
                _logger.exception(
                    "failed sending mail via Resend (id: %s) due to %s",
                    mail.id,
                    failure_reason,
                )
                mail.write({
                    "state": "exception",
                    "failure_type": "mail_smtp",
                    "failure_reason": failure_reason,
                })
                mail._postprocess_sent_message(
                    success_pids=success_pids,
                    success_emails=success_emails,
                    failure_reason=failure_reason,
                    failure_type="mail_smtp",
                )
                if raise_exception:
                    if isinstance(exc, MailDeliveryException):
                        raise
                    raise MailDeliveryException(failure_reason) from exc

        if post_send_callback:
            post_send_callback(self.ids)
        return True
