from odoo import api, fields, models, _
from odoo.exceptions import ValidationError


class KiiraayeElection(models.Model):
    _name = "kiiraaye.election"
    _description = "Historique des élections"
    _rec_name = "name"
    _order = "date desc, id desc"

    name = fields.Char(string="Élection", required=True, index=True)
    date = fields.Date(string="Date du scrutin", required=True, index=True)
    election_type = fields.Selection(
        [
            ("presidentielle", "Présidentielle"),
            ("legislative", "Législative"),
            ("locale", "Locale"),
            ("referendum", "Référendum"),
            ("autre", "Autre"),
        ],
        string="Type",
        required=True,
        default="presidentielle",
    )
    source = fields.Char(string="Source", required=True)
    source_url = fields.Char(string="URL source")
    notes = fields.Text(string="Notes")
    active = fields.Boolean(string="Actif", default=True)
    result_ids = fields.One2many(
        "kiiraaye.election.result",
        "election_id",
        string="Résultats territoriaux",
    )

    _unique_election = models.Constraint(
        "UNIQUE(name, date)",
        "Cette élection existe déjà pour cette date.",
    )




# Données définitives de l'élection présidentielle du 24 mars 2024,
# par département. Source : Conseil constitutionnel, Décision n° 7/E/2024,
# résultats définitifs compilés dans l'Annexe II du rapport de la MOE UE.
PRESIDENTIAL_2024_DEPARTMENT_RESULTS = {
    "Dakar": (707816, 457600, 2206, 455394, 286846),
    "Guediawaye": (203274, 127953, 586, 127367, 79646),
    "Keur Massar": (249588, 146038, 724, 145314, 93646),
    "Pikine": (391278, 243713, 1214, 242499, 157931),
    "Rufisque": (277865, 187166, 1028, 186138, 106505),
    "Bambey": (128264, 76719, 631, 76088, 50245),
    "Diourbel": (124483, 74906, 583, 74323, 44809),
    "Mbacke": (383046, 217979, 1541, 216438, 172053),
    "Fatick": (171291, 93067, 680, 92387, 38813),
    "Foundiougne": (130217, 79455, 587, 78868, 35927),
    "Gossas": (47017, 28482, 954, 27528, 13046),
    "Birkilane": (51085, 34150, 223, 33927, 18535),
    "Kaffrine": (98791, 66520, 577, 65943, 33107),
    "Koungheul": (77835, 51191, 537, 50654, 21591),
    "Malem Hodar": (40413, 26701, 265, 26436, 11980),
    "Guinguineo": (58558, 37121, 220, 36901, 17481),
    "Kaolack": (253829, 147752, 953, 146799, 82960),
    "Nioro du Rip": (152050, 100153, 788, 99365, 51702),
    "Kedougou": (41434, 23609, 305, 23304, 10064),
    "Salemata": (11481, 6866, 76, 6790, 1826),
    "Saraya": (19498, 11978, 132, 11846, 7012),
    "Kolda": (106611, 68863, 598, 68265, 30256),
    "Medina Yoro Foulah": (46254, 31479, 419, 31060, 13540),
    "Velingara": (112746, 72671, 906, 71765, 28563),
    "Kebemer": (133832, 84990, 679, 84311, 49443),
    "Linguere": (133089, 79043, 891, 78152, 22449),
    "Louga": (193718, 125760, 1017, 124743, 57021),
    "Kanel": (117723, 65345, 872, 64473, 5644),
    "Matam": (170744, 101594, 1133, 100461, 10620),
    "Ranerou Ferlo": (27396, 15868, 269, 15599, 1239),
    "Dagana": (150197, 93044, 673, 92371, 35462),
    "Podor": (237079, 135282, 1347, 133935, 10941),
    "Saint louis": (176366, 111234, 630, 110604, 62793),
    "Bounkiling": (64210, 40115, 332, 39783, 22359),
    "Goudomp": (73097, 46683, 1447, 45236, 28697),
    "Sedhiou": (72957, 45582, 277, 45305, 28964),
    "Bakel": (66767, 35120, 443, 34677, 11102),
    "Goudiry": (48425, 27555, 384, 27171, 5866),
    "Koumpentoum": (52967, 36806, 435, 36371, 11486),
    "Tambacounda": (118990, 68215, 817, 67398, 27680),
    "Mbour": (351023, 227572, 1388, 226184, 139582),
    "Thies": (395942, 255771, 1485, 254286, 152047),
    "Tivaouane": (256345, 173184, 1167, 172017, 98403),
    "Bignona": (140315, 85212, 383, 84829, 68929),
    "Oussouye": (33287, 19980, 89, 19891, 15824),
    "Ziguinchor": (134657, 76813, 490, 76323, 57003),
}

PRESIDENTIAL_2024_SOURCE = (
    "Conseil constitutionnel — Décision n° 7/E/2024 ; "
    "Annexe II, résultats définitifs par départements."
)
PRESIDENTIAL_2024_SOURCE_URL = (
    "https://dge.sn/wp-content/uploads/2024/09/decision-7-E-resultats-election.pdf"
)

class KiiraayeElectionResult(models.Model):
    _name = "kiiraaye.election.result"
    _description = "Résultat électoral historique"
    _rec_name = "display_name"
    _order = "election_id, geographie_id"

    election_id = fields.Many2one(
        "kiiraaye.election",
        string="Élection",
        required=True,
        ondelete="cascade",
        index=True,
    )
    scope = fields.Selection(
        [
            ("global", "Résultat global"),
            ("geographique", "Résultat géographique"),
        ],
        string="Portée",
        required=True,
        default="geographique",
        index=True,
    )
    geographie_id = fields.Many2one(
        "kiiraaye.geographie",
        string="Région / Département / Commune",
        ondelete="cascade",
        index=True,
    )
    registered_voters = fields.Integer(
        string="Électeurs inscrits",
        default=0,
    )
    voters = fields.Integer(
        string="Votants",
        default=0,
    )
    null_votes = fields.Integer(
        string="Bulletins nuls / blancs",
        default=0,
    )
    valid_votes = fields.Integer(
        string="Suffrages valablement exprimés",
        default=0,
    )
    diomaye_president_votes = fields.Integer(
        string="Voix Diomaye Président",
        default=0,
        help="Nombre de voix obtenues par Bassirou Diomaye Diakhar Faye.",
    )
    diomaye_president_pct = fields.Float(
        string="% Diomaye Président",
        compute="_compute_diomaye_president_pct",
        digits=(16, 2),
    )
    source = fields.Char(string="Source")
    notes = fields.Text(string="Notes")
    display_name = fields.Char(
        string="Libellé",
        compute="_compute_display_name",
    )

    @api.depends("valid_votes", "diomaye_president_votes")
    def _compute_diomaye_president_pct(self):
        for record in self:
            record.diomaye_president_pct = (
                round(
                    record.diomaye_president_votes / record.valid_votes * 100,
                    2,
                )
                if record.valid_votes
                else 0.0
            )

    @api.depends("election_id.name", "geographie_id.name", "scope")
    def _compute_display_name(self):
        for record in self:
            if record.scope == "global":
                record.display_name = f"{record.election_id.name or ''} — Global"
            else:
                record.display_name = (
                    f"{record.election_id.name or ''} — "
                    f"{record.geographie_id.name or 'Zone'}"
                )

    @api.model
    def ensure_presidential_2024_department_results(self, election):
        """Crée les résultats départementaux officiels 2024 manquants.

        Les 14 régions sont calculées ensuite par agrégation des départements.
        Les communes restent volontairement vides tant qu'une source complète
        et vérifiable à ce niveau n'est pas disponible.
        """
        if (
            not election
            or election.election_type != "presidentielle"
            or not election.date
            or election.date.year != 2024
        ):
            return 0

        Geography = self.env["kiiraaye.geographie"]
        country = self.env["res.country"].search([("code", "=", "SN")], limit=1)
        if not country:
            return 0

        departments = Geography.search([
            ("active", "=", True),
            ("country_id", "=", country.id),
            ("niveau", "=", "niveau2"),
        ])
        normalized_departments = {}
        for geography in departments:
            key = self._normalize_result_name(geography.name)
            normalized_departments.setdefault(key, geography)

        created = 0
        for raw_name, values in PRESIDENTIAL_2024_DEPARTMENT_RESULTS.items():
            geography = normalized_departments.get(self._normalize_result_name(raw_name))
            if not geography:
                continue
            existing = self.search([
                ("election_id", "=", election.id),
                ("scope", "=", "geographique"),
                ("geographie_id", "=", geography.id),
            ], limit=1)
            registered, voters, null_votes, valid_votes, diomaye_votes = values
            vals = {
                "election_id": election.id,
                "scope": "geographique",
                "geographie_id": geography.id,
                "registered_voters": registered,
                "voters": voters,
                "null_votes": null_votes,
                "valid_votes": valid_votes,
                "diomaye_president_votes": diomaye_votes,
                "source": PRESIDENTIAL_2024_SOURCE,
                "notes": "Données définitives par département ; les agrégats régionaux sont calculés automatiquement.",
            }
            if existing:
                # Ne corrige pas une saisie manuelle : la source permet de
                # distinguer les données de référence déjà chargées.
                if existing.source == PRESIDENTIAL_2024_SOURCE:
                    existing.write(vals)
            else:
                self.create(vals)
                created += 1
        return created

    @staticmethod
    def _normalize_result_name(value):
        import unicodedata

        value = unicodedata.normalize("NFKD", value or "")
        value = "".join(ch for ch in value if not unicodedata.combining(ch))
        value = value.upper().replace("-", " ").replace("'", " ")
        return " ".join(value.split())

    @api.constrains(
        "scope",
        "geographie_id",
        "registered_voters",
        "voters",
        "null_votes",
        "valid_votes",
        "diomaye_president_votes",
    )
    def _check_result_values(self):
        for record in self:
            if record.scope == "global" and record.geographie_id:
                raise ValidationError(
                    _("Un résultat global ne doit pas avoir de zone géographique.")
                )
            if record.scope == "geographique" and not record.geographie_id:
                raise ValidationError(
                    _("Un résultat géographique doit être rattaché à une zone.")
                )
            for field_name in (
                "registered_voters",
                "voters",
                "null_votes",
                "valid_votes",
                "diomaye_president_votes",
            ):
                if getattr(record, field_name) < 0:
                    raise ValidationError(
                        _("Les valeurs électorales ne peuvent pas être négatives.")
                    )
            if record.voters > record.registered_voters and record.registered_voters:
                raise ValidationError(
                    _("Le nombre de votants ne peut pas dépasser les inscrits.")
                )
            if record.valid_votes > record.voters and record.voters:
                raise ValidationError(
                    _(
                        "Les suffrages valablement exprimés ne peuvent pas dépasser les votants."
                    )
                )
            if (
                record.diomaye_president_votes > record.valid_votes
                and record.valid_votes
            ):
                raise ValidationError(
                    _(
                        "Les voix de Diomaye Président ne peuvent pas dépasser les "
                        "suffrages valablement exprimés."
                    )
                )

    def participation_pct(self):
        self.ensure_one()
        return (
            round(self.voters / self.registered_voters * 100, 2)
            if self.registered_voters
            else 0.0
        )

    def valid_pct_of_voters(self):
        self.ensure_one()
        return (
            round(self.valid_votes / self.voters * 100, 2)
            if self.voters
            else 0.0
        )
