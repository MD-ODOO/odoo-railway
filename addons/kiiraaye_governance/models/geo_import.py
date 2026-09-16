import json
from urllib.request import Request, urlopen
from urllib.error import HTTPError, URLError

from odoo import fields, models, _
from odoo.exceptions import UserError


class KiiraayeGeoImportWizard(models.TransientModel):
    _name = "kiiraaye.geo.import.wizard"
    _description = "Import du référentiel géographique mondial"

    country_id = fields.Many2one("res.country", string="Pays")
    boundary_type = fields.Selection([
        ("ADM0", "ADM0 — Pays"),
        ("ADM1", "ADM1 — Région / État / Province"),
        ("ADM2", "ADM2 — Département / Comté / District"),
        ("ADM3", "ADM3 — Commune / Municipalité / Ville"),
        ("ADM4", "ADM4 — Niveau local"),
        ("ADM5", "ADM5 — Quartier / district de proximité"),
    ], required=True, default="ADM1")
    simplified = fields.Boolean(string="Géométrie simplifiée", default=True)
    update_existing = fields.Boolean(string="Mettre à jour les données existantes", default=True)
    message = fields.Text(readonly=True)

    def _get_json(self, url):
        req = Request(url, headers={"User-Agent": "Kiiraaye-Odoo/19"})
        try:
            with urlopen(req, timeout=120) as response:
                return json.loads(response.read().decode("utf-8"))
        except (HTTPError, URLError, TimeoutError) as exc:
            raise UserError(_("Connexion à la source géographique impossible : %s") % exc)

    def _iso3(self):
        # geoBoundaries exige ISO-3166 alpha-3. On utilise les codes ISO-3
        # fournis par Odoo lorsqu'ils sont disponibles via la table de mapping.
        mapping = {
            "SN":"SEN","FR":"FRA","US":"USA","CA":"CAN","GB":"GBR","DE":"DEU",
            "IT":"ITA","ES":"ESP","BE":"BEL","CH":"CHE","CI":"CIV","ML":"MLI",
            "MR":"MRT","GN":"GIN","GW":"GNB","GM":"GMB","MA":"MAR","DZ":"DZA",
            "TN":"TUN","CM":"CMR","PT":"PRT","BR":"BRA","AR":"ARG","IN":"IND",
            "CN":"CHN","JP":"JPN","AU":"AUS","ZA":"ZAF","KE":"KEN","NG":"NGA",
        }
        if not self.country_id:
            return "ALL"
        iso3 = mapping.get((self.country_id.code or "").upper())
        if not iso3:
            raise UserError(_(
                "Le pays %s n'a pas encore de correspondance ISO-2 → ISO-3 dans le module."
            ) % self.country_id.display_name)
        return iso3

    def _normalized_level(self, adm):
        return {
            0: "pays", 1: "region", 2: "departement", 3: "commune",
            4: "communaute_rurale", 5: "quartier",
        }.get(adm, "autre")

    def _root_country(self, country):
        Geo = self.env["kiiraaye.geographie"]
        root = Geo.search([("niveau", "=", "pays"), ("country_id", "=", country.id), ("parent_id", "=", False)], limit=1)
        if not root:
            root = Geo.create({
                "name": country.name,
                "code": "COUNTRY-%s" % (country.code or country.id),
                "niveau": "pays",
                "admin_level": 0,
                "country_id": country.id,
                "source_name": "Odoo res.country",
            })
        return root

    def _find_parent(self, level, prop, country):
        if level <= 1:
            return self._root_country(country)
        Geo = self.env["kiiraaye.geographie"]
        parent_level = self._normalized_level(level - 1)
        parent_name = (
            prop.get("shapeGroup") or prop.get("parentName") or
            prop.get("shapeParentName") or prop.get("admin1Name")
        )
        if parent_name:
            parent = Geo.search([
                ("country_id", "=", country.id), ("niveau", "=", parent_level),
                ("name", "=", parent_name),
            ], limit=1)
            if parent:
                return parent
        return self._root_country(country)

    def action_import(self):
        self.ensure_one()
        iso3 = self._iso3()
        meta = self._get_json(
            f"https://www.geoboundaries.org/api/current/gbOpen/{iso3}/{self.boundary_type}/"
        )
        items = [meta] if isinstance(meta, dict) else (meta if isinstance(meta, list) else [])
        if not items:
            raise UserError(_("Aucune couche retournée par geoBoundaries."))

        Geo = self.env["kiiraaye.geographie"]
        created = updated = 0
        for info in items:
            geo_url = info.get("simplifiedGeometryGeoJSON") if self.simplified else info.get("gjDownloadURL")
            if not geo_url:
                geo_url = info.get("gjDownloadURL") or info.get("simplifiedGeometryGeoJSON")
            if not geo_url:
                continue
            geo = self._get_json(geo_url)
            features = geo.get("features", []) if isinstance(geo, dict) else []
            for feature in features:
                prop = feature.get("properties") or {}
                name = prop.get("shapeName") or prop.get("NAME") or prop.get("name") or prop.get("name_en")
                if not name:
                    continue
                uid = str(prop.get("shapeID") or prop.get("GID") or feature.get("id") or name)
                level = int(str(prop.get("shapeLevel") or self.boundary_type.replace("ADM", "1")).replace("ADM", ""))
                country = self.country_id
                if not country:
                    c_name = info.get("boundaryName") or ""
                    country = self.env["res.country"].search([("name", "=", c_name)], limit=1)
                if not country:
                    continue
                code = f"{iso3}-{self.boundary_type}-{uid}"[:250]
                state = False
                if level == 1:
                    State = self.env["res.country.state"]
                    state_code = (prop.get("shapeISO") or prop.get("shapeCode") or uid)[-3:].upper()
                    state = State.search([("country_id", "=", country.id), ("code", "=", state_code)], limit=1)
                    if not state:
                        state = State.create({"name": name, "code": state_code, "country_id": country.id})
                    elif state.name != name and self.update_existing:
                        state.write({"name": name})
                vals = {
                    "name": name, "code": code, "niveau": self._normalized_level(level),
                    "admin_level": level, "country_id": country.id,
                    "state_id": state.id if state else False,
                    "parent_id": self._find_parent(level, prop, country).id,
                    "source_name": "geoBoundaries / gbOpen",
                    "source_uid": uid,
                    "source_year": str(info.get("boundaryYearRepresented") or ""),
                    "source_license": str(info.get("boundaryLicense") or "CC BY 4.0"),
                    "source_url": str(info.get("licenseSource") or info.get("gjDownloadURL") or ""),
                    "geojson": json.dumps(feature.get("geometry"), ensure_ascii=False),
                }
                existing = Geo.search([("source_name", "=", vals["source_name"]), ("source_uid", "=", uid)], limit=1)
                if existing:
                    if self.update_existing:
                        existing.write(vals)
                        updated += 1
                else:
                    Geo.create(vals)
                    created += 1

        self.message = _("Import terminé : %s créé(s), %s mis à jour.") % (created, updated)
        return {
            "type": "ir.actions.act_window", "res_model": "kiiraaye.geo.import.wizard",
            "view_mode": "form", "res_id": self.id, "target": "new",
        }


class KiiraayeGeoBootstrap(models.TransientModel):
    _name = "kiiraaye.geo.bootstrap"
    _description = "Initialisation du référentiel des pays"

    def action_bootstrap_countries(self):
        Geo = self.env["kiiraaye.geographie"]
        countries = self.env["res.country"].search([])
        created = 0
        for country in countries:
            root = Geo.search([
                ("niveau", "=", "pays"), ("country_id", "=", country.id), ("parent_id", "=", False)
            ], limit=1)
            if not root:
                Geo.create({
                    "name": country.name,
                    "code": "COUNTRY-%s" % (country.code or country.id),
                    "niveau": "pays", "admin_level": 0, "country_id": country.id,
                    "source_name": "Odoo res.country",
                })
                created += 1
        return {
            "type": "ir.actions.client", "tag": "display_notification",
            "params": {"title": _("Référentiel géographique"),
                       "message": _("%s pays initialisés.") % created,
                       "type": "success", "sticky": False},
        }
