from odoo import fields, models


class KiiraayeOrganisationType(models.Model):
    _name = "kiiraaye.organisation.type"
    _description = "Type / niveau d'organisation Kiiraaye"
    _rec_name = "name"
    _order = "niveau, sequence, name"

    name = fields.Char(
        string="Nom du type",
        required=True,
        index=True,
    )
    code = fields.Char(
        string="Code",
        required=True,
        copy=False,
        index=True,
    )
    niveau = fields.Integer(
        string="Niveau",
        default=1,
        required=True,
        help="Niveau hiérarchique ou fonctionnel du type d'organisation.",
    )
    sequence = fields.Integer(
        string="Séquence",
        default=10,
    )
    description = fields.Text(
        string="Description",
    )
    active = fields.Boolean(
        string="Actif",
        default=True,
    )

    _unique_code = models.Constraint(
        "UNIQUE(code)",
        "Le code du type d'organisation doit être unique.",
    )
