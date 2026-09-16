from odoo import http
from odoo.http import request


class KiiraayeMemberCardController(http.Controller):

    @http.route(
        "/kiiraaye/card/verify/<string:token>",
        type="http",
        auth="public",
        methods=["GET"],
        csrf=False,
    )
    def verify_card(self, token, **kwargs):
        card = request.env["kiiraaye.member.card"].sudo().search(
            [("verification_token", "=", token)],
            limit=1,
        )
        if not card:
            return request.make_response(
                "<h2>Carte invalide</h2><p>Cette référence de carte n'existe pas.</p>",
                headers=[("Content-Type", "text/html; charset=utf-8")],
                status=404,
            )

        if card.state != "active":
            label = dict(card._fields["state"].selection).get(card.state, card.state)
            return request.make_response(
                f"<h2>Carte non valide</h2><p>Statut : {label}</p>",
                headers=[("Content-Type", "text/html; charset=utf-8")],
                status=200,
            )

        return request.make_response(
            "<html><body>"
            "<h2>Carte Kiiraaye valide</h2>"
            f"<p><strong>Matricule :</strong> {card.partisan_id.matricule}</p>"
            f"<p><strong>Nom :</strong> {card.partisan_id.prenom} {card.partisan_id.nom}</p>"
            f"<p><strong>Section :</strong> {card.section_id.name}</p>"
            f"<p><strong>Territoire :</strong> {card.geographie_id.complete_name}</p>"
            "</body></html>",
            headers=[("Content-Type", "text/html; charset=utf-8")],
            status=200,
        )
