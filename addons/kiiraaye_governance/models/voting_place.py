# -*- coding: utf-8 -*-
"""Référentiel électoral historique : centres, bureaux et affectation des membres."""
import hashlib
import json
import logging
import re
import unicodedata
import uuid
from urllib.error import HTTPError, URLError
from urllib.parse import quote
from urllib.request import Request, urlopen

from odoo import api, fields, models, _
from odoo.exceptions import UserError, ValidationError

_logger = logging.getLogger(__name__)
_API_BASE = "https://www.vie-publique.sn/api/elections/map/department-details/"
_SOURCE = "Vie-Publique.sn — carte électorale 2024"
_SOURCE_URL = "https://www.vie-publique.sn/elections-senegal/carte-electorale/nationale"
_YEAR = 2024
_BATCH_SIZE = 4


def _normalize(value):
    value = unicodedata.normalize("NFKD", str(value or ""))
    value = "".join(ch for ch in value if not unicodedata.combining(ch))
    return re.sub(r"[^A-Z0-9]+", "", value.upper())


def _uid(prefix, *values):
    raw = "|".join(_normalize(value) for value in values)
    return prefix + hashlib.sha1(raw.encode("utf-8")).hexdigest()[:20]


def _integer(value):
    try:
        return max(0, int(value or 0))
    except (TypeError, ValueError):
        return 0


class KiiraayeCentreVote(models.Model):
    _name = "kiiraaye.centre.vote"
    _description = "Centre de vote"
    _rec_name = "name"
    _order = "region_id, departement_id, commune_id, name, id"

    name = fields.Char(string="Centre de vote / lieu de vote", required=True, index=True)
    source_uid = fields.Char(required=True, default=lambda self: "MANUAL-C-" + uuid.uuid4().hex, copy=False, index=True)
    country_id = fields.Many2one("res.country", string="Pays", required=True, default=lambda self: self.env["res.country"].search([("code", "=", "SN")], limit=1), index=True, ondelete="restrict")
    region_id = fields.Many2one("kiiraaye.geographie", string="Région", index=True, ondelete="set null")
    departement_id = fields.Many2one("kiiraaye.geographie", string="Département", index=True, ondelete="set null")
    commune_id = fields.Many2one("kiiraaye.geographie", string="Commune", index=True, ondelete="set null")
    region_label = fields.Char(string="Région source")
    departement_label = fields.Char(string="Département source")
    commune_label = fields.Char(string="Commune source")
    locality_name = fields.Char(string="Localité / commune source", index=True)
    election_year = fields.Integer(string="Année des données électorales", default=_YEAR, required=True, index=True)
    source = fields.Char(string="Source", default=_SOURCE, readonly=True)
    source_url = fields.Char(string="URL de la source", default=_SOURCE_URL, readonly=True)
    latitude = fields.Float(string="Latitude", digits=(10, 7), help="Coordonnée GPS précise facultative; la source consultée n'en fournit pas pour chaque centre.")
    longitude = fields.Float(string="Longitude", digits=(10, 7), help="Coordonnée GPS précise facultative; la source consultée n'en fournit pas pour chaque centre.")
    active = fields.Boolean(string="Actif", default=True, index=True)
    bureau_ids = fields.One2many("kiiraaye.bureau.vote", "centre_id", string="Bureaux")
    bureau_count = fields.Integer(string="Nombre de bureaux", compute="_compute_voting_totals")
    registered_voters = fields.Integer(string="Électeurs inscrits", compute="_compute_voting_totals")
    member_count = fields.Integer(string="Membres Kiiraaye", compute="_compute_member_count")
    members_to_voters_pct = fields.Float(string="Membres / électeurs (%)", compute="_compute_member_count", digits=(6, 2))

    _unique_source_uid = models.Constraint("UNIQUE(source_uid)", "L'identifiant source d'un centre de vote doit être unique.")

    @api.depends("bureau_ids", "bureau_ids.registered_voters")
    def _compute_voting_totals(self):
        for centre in self:
            centre.bureau_count = len(centre.bureau_ids)
            centre.registered_voters = sum(centre.bureau_ids.mapped("registered_voters"))

    @api.depends("bureau_ids", "country_id")
    def _compute_member_count(self):
        Partisan = self.env["kiiraaye.partisan"].sudo()
        for centre in self:
            count = Partisan.search_count([("active", "=", True), ("centre_vote_id", "=", centre.id)]) if centre.id else 0
            centre.member_count = count
            centre.members_to_voters_pct = round(count / centre.registered_voters * 100, 2) if centre.registered_voters else 0.0

    @api.constrains("country_id", "region_id", "departement_id", "commune_id")
    def _check_voting_hierarchy(self):
        for centre in self:
            for geo in (centre.region_id, centre.departement_id, centre.commune_id):
                if geo and centre.country_id and geo.country_id != centre.country_id:
                    raise ValidationError(_("Les zones du centre de vote doivent appartenir au même pays."))
            if centre.departement_id and centre.region_id and centre.departement_id.parent_id != centre.region_id:
                raise ValidationError(_("Le département doit appartenir à la région sélectionnée."))
            if centre.commune_id and centre.departement_id and centre.commune_id.parent_id != centre.departement_id:
                raise ValidationError(_("La commune doit appartenir au département sélectionné."))


class KiiraayeBureauVote(models.Model):
    _name = "kiiraaye.bureau.vote"
    _description = "Bureau de vote"
    _rec_name = "name"
    _order = "region_id, departement_id, commune_id, centre_id, office_number, id"

    name = fields.Char(string="Bureau de vote", required=True, index=True)
    source_uid = fields.Char(required=True, default=lambda self: "MANUAL-B-" + uuid.uuid4().hex, copy=False, index=True)
    centre_id = fields.Many2one("kiiraaye.centre.vote", string="Centre de vote", required=True, index=True, ondelete="cascade")
    country_id = fields.Many2one("res.country", related="centre_id.country_id", store=True, index=True)
    region_id = fields.Many2one("kiiraaye.geographie", string="Région", related="centre_id.region_id", store=True, index=True)
    departement_id = fields.Many2one("kiiraaye.geographie", string="Département", related="centre_id.departement_id", store=True, index=True)
    commune_id = fields.Many2one("kiiraaye.geographie", string="Commune", related="centre_id.commune_id", store=True, index=True)
    region_label = fields.Char(related="centre_id.region_label", store=True)
    departement_label = fields.Char(related="centre_id.departement_label", store=True)
    commune_label = fields.Char(related="centre_id.commune_label", store=True)
    locality_name = fields.Char(related="centre_id.locality_name", store=True)
    office_number = fields.Integer(string="N° de bureau", required=True, index=True)
    registered_voters = fields.Integer(string="Électeurs inscrits", default=0, required=True)
    implantation = fields.Char(string="Implantation / salle")
    election_year = fields.Integer(string="Année des données électorales", default=_YEAR, required=True, index=True)
    source = fields.Char(string="Source", default=_SOURCE, readonly=True)
    source_url = fields.Char(string="URL de la source", default=_SOURCE_URL, readonly=True)
    latitude = fields.Float(related="centre_id.latitude", digits=(10, 7), store=True)
    longitude = fields.Float(related="centre_id.longitude", digits=(10, 7), store=True)
    active = fields.Boolean(string="Actif", default=True, index=True)
    member_count = fields.Integer(string="Membres Kiiraaye", compute="_compute_member_count")

    _unique_source_uid = models.Constraint("UNIQUE(source_uid)", "L'identifiant source d'un bureau de vote doit être unique.")

    @api.depends("centre_id")
    def _compute_member_count(self):
        Partisan = self.env["kiiraaye.partisan"].sudo()
        for bureau in self:
            bureau.member_count = Partisan.search_count([("active", "=", True), ("bureau_vote_id", "=", bureau.id)]) if bureau.id else 0


class ResCountryVotingPlaceImport(models.Model):
    _inherit = "res.country"

    kiiraaye_vote_import_running = fields.Boolean(string="Import des centres/bureaux en cours", default=False, readonly=True, copy=False)
    kiiraaye_vote_import_offset = fields.Integer(string="Départements traités pour l'import électoral", default=0, readonly=True, copy=False)
    kiiraaye_vote_import_count = fields.Integer(string="Bureaux importés", default=0, readonly=True, copy=False)
    kiiraaye_vote_import_message = fields.Text(string="État de l'import des centres/bureaux", readonly=True, copy=False)

    @staticmethod
    def _voting_api_get(url):
        request = Request(url, headers={"User-Agent": "Kiiraaye-Gouvernance/19.0", "Accept": "application/json"})
        try:
            with urlopen(request, timeout=60) as response:
                payload = json.loads(response.read().decode("utf-8"))
        except (HTTPError, URLError, TimeoutError, ValueError) as exc:
            raise UserError(_("L'API électorale n'a pas répondu correctement. URL : %s. Détail : %s") % (url, exc))
        if not isinstance(payload, dict) or not isinstance(payload.get("data"), list):
            raise UserError(_("La réponse de l'API électorale n'a pas le format attendu : %s") % url)
        return payload["data"]

    @staticmethod
    def _voting_geo_maps(country):
        geos = country.env["kiiraaye.geographie"].sudo().search([
            ("country_id", "=", country.id), ("active", "=", True),
            ("niveau", "in", ["niveau1", "niveau2", "niveau3"]),
        ])
        maps = {"niveau1": {}, "niveau2": {}, "niveau3": {}, "communes_by_parent_name": {}}
        for geo in geos:
            key = _normalize(geo.name)
            maps[geo.niveau].setdefault(key, geo)
            if geo.niveau == "niveau3" and geo.parent_id:
                maps["communes_by_parent_name"][(geo.parent_id.id, key)] = geo
        return maps

    def _import_voting_department(self, department, geo_maps):
        self.ensure_one()
        url = _API_BASE + quote(department.name, safe="")
        rows = self._voting_api_get(url)
        Centre = self.env["kiiraaye.centre.vote"].sudo()
        Bureau = self.env["kiiraaye.bureau.vote"].sudo()
        seen_centres = {}
        for row in rows:
            place = str(row.get("polling_place") or "").strip()
            if not place:
                continue
            dep_name = str(row.get("department") or department.name).strip()
            reg_name = str(row.get("region") or (department.parent_id.name if department.parent_id else "")).strip()
            commune_name = str(row.get("municipality") or "").strip()
            try:
                office = int(row.get("office_number") or 0)
            except (TypeError, ValueError):
                continue
            if office < 1:
                continue

            dept_geo = geo_maps["niveau2"].get(_normalize(dep_name)) or department
            region_geo = dept_geo.parent_id or geo_maps["niveau1"].get(_normalize(reg_name))
            commune_geo = geo_maps["communes_by_parent_name"].get((dept_geo.id, _normalize(commune_name)))
            if not commune_geo:
                fallback = geo_maps["niveau3"].get(_normalize(commune_name))
                if fallback and fallback.parent_id == dept_geo:
                    commune_geo = fallback

            centre_uid = _uid("VP2024-C-", dep_name, commune_name, place)
            centre_values = {
                "name": place, "source_uid": centre_uid, "country_id": self.id,
                "region_id": region_geo.id if region_geo else False,
                "departement_id": dept_geo.id if dept_geo else False,
                "commune_id": commune_geo.id if commune_geo else False,
                "region_label": reg_name, "departement_label": dep_name,
                "commune_label": commune_name, "locality_name": commune_name,
                "election_year": _YEAR, "source": _SOURCE, "source_url": _SOURCE_URL,
                "active": True,
            }
            centre = seen_centres.get(centre_uid)
            if not centre:
                centre = Centre.search([("source_uid", "=", centre_uid)], limit=1)
            if centre:
                centre.write(centre_values)
            else:
                centre = Centre.create(centre_values)
            seen_centres[centre_uid] = centre

            external_id = row.get("id")
            bureau_uid = "VP2024-B-" + str(external_id) if external_id not in (None, "") else _uid("VP2024-B-", centre_uid, office)
            bureau_values = {
                "name": _("Bureau %s — %s") % (office, place),
                "source_uid": bureau_uid, "centre_id": centre.id, "office_number": office,
                "registered_voters": _integer(row.get("voters")),
                "implantation": str(row.get("implantation") or "").strip(),
                "election_year": _YEAR, "source": _SOURCE, "source_url": url, "active": True,
            }
            bureau = Bureau.search([("source_uid", "=", bureau_uid)], limit=1)
            if bureau:
                bureau.write(bureau_values)
            else:
                Bureau.create(bureau_values)
        return len(rows)

    def action_start_voting_place_import(self):
        self.ensure_one()
        if self.code != "SN":
            raise UserError(_("L'import des centres et bureaux de vote est réservé au Sénégal."))
        if self.kiiraaye_vote_import_running:
            return {"type": "ir.actions.client", "tag": "display_notification", "params": {
                "title": _("Import déjà en cours"),
                "message": self.kiiraaye_vote_import_message or _("L'import électoral est déjà en cours."),
                "type": "warning", "sticky": False,
            }}
        self.sudo().write({
            "kiiraaye_vote_import_running": True, "kiiraaye_vote_import_offset": 0,
            "kiiraaye_vote_import_count": 0,
            "kiiraaye_vote_import_message": _("Import de la carte électorale 2024 lancé. Le traitement est effectué par lots en arrière-plan."),
        })
        return {"type": "ir.actions.client", "tag": "display_notification", "params": {
            "title": _("Import électoral lancé"),
            "message": _("Consultez l'état sur la fiche du Sénégal. Les données source sont celles de 2024."),
            "type": "success", "sticky": False,
        }}

    @api.model
    def action_process_voting_place_import(self):
        countries = self.sudo().search([("code", "=", "SN"), ("kiiraaye_vote_import_running", "=", True)])
        Centre = self.env["kiiraaye.centre.vote"].sudo()
        Bureau = self.env["kiiraaye.bureau.vote"].sudo()
        for country in countries:
            try:
                departments = self.env["kiiraaye.geographie"].sudo().search([
                    ("country_id", "=", country.id), ("niveau", "=", "niveau2"), ("active", "=", True),
                ], order="name, id")
                if not departments:
                    raise UserError(_("Aucun département actif n'est trouvé. Chargez d'abord le référentiel géographique du Sénégal."))
                offset = max(0, country.kiiraaye_vote_import_offset or 0)
                batch = departments[offset:offset + _BATCH_SIZE]
                if not batch:
                    offset = 0
                    batch = departments[:_BATCH_SIZE]
                geo_maps = self._voting_geo_maps(country)
                processed = []
                for department in batch:
                    row_count = country._import_voting_department(department, geo_maps)
                    processed.append("%s (%s lignes)" % (department.name, row_count))
                new_offset = offset + len(batch)
                finished = new_offset >= len(departments)
                centre_count = Centre.search_count([("country_id", "=", country.id), ("election_year", "=", _YEAR), ("active", "=", True)])
                bureau_count = Bureau.search_count([("country_id", "=", country.id), ("election_year", "=", _YEAR), ("active", "=", True)])
                message = _("Import %s : %s centres, %s bureaux enregistrés. Dernier lot : %s.") % (
                    _("terminé" if finished else "en cours"), centre_count, bureau_count, "; ".join(processed)
                )
                if finished:
                    message += _(" Source : carte électorale 2024 de Vie-Publique.sn. Les coordonnées GPS ne sont pas fournies par cette source.")
                country.sudo().write({
                    "kiiraaye_vote_import_running": not finished,
                    "kiiraaye_vote_import_offset": 0 if finished else new_offset,
                    "kiiraaye_vote_import_count": bureau_count,
                    "kiiraaye_vote_import_message": message,
                })
            except Exception as exc:
                _logger.exception("Échec de l'import des centres et bureaux de vote")
                country.sudo().write({
                    "kiiraaye_vote_import_running": False,
                    "kiiraaye_vote_import_message": _("Import arrêté; relancez-le après vérification de l'API. Détail : %s") % str(exc),
                })
        return True


class KiiraayeDashboardVotingPlaces(models.Model):
    _inherit = "kiiraaye.dashboard"

    @api.model
    def _voting_grouped(self, Model, domain, group_field, sum_field=None):
        aggregates = ["__count"] + (["%s:sum" % sum_field] if sum_field else [])
        output = {}
        for values in Model.sudo()._read_group(domain, [group_field], aggregates):
            record = values[0]
            output[record.id if record else False] = {
                "count": int(values[1] or 0),
                "sum": int(values[2] or 0) if sum_field else 0,
            }
        return output

    @api.model
    def _voting_places_overview(self, Partisan):
        country = self.env["res.country"].sudo().search([("code", "=", "SN")], limit=1)
        Centre = self.env["kiiraaye.centre.vote"]
        Bureau = self.env["kiiraaye.bureau.vote"]
        Geography = self.env["kiiraaye.geographie"]
        base = [("active", "=", True), ("election_year", "=", _YEAR)]
        centre_domain = base + ([("country_id", "=", country.id)] if country else [("id", "=", False)])
        bureau_domain = base + ([("country_id", "=", country.id)] if country else [("id", "=", False)])
        member_domain = ["&", ("active", "=", True), "|", ("country_id.code", "=", "SN"), ("region_id.country_id.code", "=", "SN")]
        linked_domain = member_domain + [("centre_vote_id", "!=", False)]
        grouped = {}
        for label, field in (("regions", "region_id"), ("departments", "departement_id"), ("communes", "commune_id")):
            grouped[label] = {
                "centres": self._voting_grouped(Centre, centre_domain, field),
                "bureaux": self._voting_grouped(Bureau, bureau_domain, field, "registered_voters"),
                "members": self._voting_grouped(Partisan, member_domain, field),
                "linked": self._voting_grouped(Partisan, linked_domain, field),
            }

        member_total = Partisan.sudo().search_count(member_domain)
        linked_total = Partisan.sudo().search_count(linked_domain)
        centre_total = Centre.sudo().search_count(centre_domain)
        bureau_total = Bureau.sudo().search_count(bureau_domain)
        voter_total = sum(item["sum"] for item in grouped["regions"]["bureaux"].values())
        total_ratio = round(member_total / voter_total * 100, 2) if voter_total else None
        geo_domain = [("active", "=", True), ("country_id.code", "=", "SN")]
        regions = Geography.sudo().search(geo_domain + [("niveau", "=", "niveau1")], order="name, id")
        departments = Geography.sudo().search(geo_domain + [("niveau", "=", "niveau2")], order="name, id")
        communes = Geography.sudo().search(geo_domain + [("niveau", "=", "niveau3")], order="name, id")
        departments_by_region, communes_by_department = {}, {}
        for department in departments:
            departments_by_region.setdefault(department.parent_id.id, []).append(department)
        for commune in communes:
            communes_by_department.setdefault(commune.parent_id.id, []).append(commune)

        def item(level, geography):
            stats = grouped[level]
            centre = stats["centres"].get(geography.id, {})
            bureau = stats["bureaux"].get(geography.id, {})
            members = stats["members"].get(geography.id, {})
            linked = stats["linked"].get(geography.id, {})
            centres_count = int(centre.get("count", 0))
            bureaux_count = int(bureau.get("count", 0))
            voters = int(bureau.get("sum", 0))
            member_count = int(members.get("count", 0))
            affiliated = int(linked.get("count", 0))
            ratio = round(member_count / voters * 100, 2) if voters else None
            color = "grey" if not bureaux_count or not voters else ("red" if ratio < 1 else "orange" if ratio < 5 else "yellow" if ratio < 10 else "green")
            return {
                "id": geography.id, "name": geography.name, "centre_count": centres_count,
                "bureau_count": bureaux_count, "registered_voters": voters, "members": member_count,
                "members_affilies": affiliated, "proportionnalite_pct": ratio, "map_class": color,
            }

        region_rows, department_rows = [], []
        for region in regions:
            region_row = item("regions", region)
            region_row["departments"] = []
            for department in departments_by_region.get(region.id, []):
                dep_row = item("departments", department)
                dep_row["region_id"] = region.id
                dep_row["communes"] = [item("communes", commune) for commune in communes_by_department.get(department.id, [])]
                region_row["departments"].append(dep_row)
                department_rows.append(dep_row)
            region_rows.append(region_row)

        return {
            "available": bool(centre_total or bureau_total),
            "source_year": _YEAR, "source": _SOURCE, "source_url": _SOURCE_URL,
            "totals": {
                "centres": centre_total, "bureaux": bureau_total, "electeurs_inscrits": voter_total,
                "membres": member_total, "membres_affilies": linked_total,
                "proportionnalite_pct": total_ratio,
            },
            "regions": region_rows, "departments": department_rows,
            "non_rattaches": {
                "centres": Centre.sudo().search_count(centre_domain + [("commune_id", "=", False)]),
                "bureaux": Bureau.sudo().search_count(bureau_domain + [("commune_id", "=", False)]),
            },
            "message": _(
                "Données électorales historiques issues de la carte électorale 2024 de Vie-Publique.sn. "
                "Les chiffres d'électeurs sont ceux de la source; l'effectif Kiiraaye est celui du système actuel. "
                "Le ratio est descriptif. L'API ne fournit pas de coordonnées GPS précises pour chaque centre."
            ),
        }
