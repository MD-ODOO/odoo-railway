import json
from urllib.request import Request, urlopen
from urllib.error import HTTPError, URLError

from odoo import fields, models, _
from odoo.exceptions import UserError


class KiiraayeGeoImportWizard(models.TransientModel):
    _name = "kiiraaye.geo.import.wizard"
    _description = "Import du référentiel géographique"

    country_id = fields.Many2one("res.country", string="Pays")
    boundary_type = fields.Selection([
        ("ADM0", "ADM0 — Pays"),
        ("ADM1", "ADM1 — Région / État"),
        ("ADM2", "ADM2 — Département / Comté"),
        ("ADM3", "ADM3 — Commune / Municipalité"),
        ("ADM4", "ADM4 — Niveau local"),
        ("ADM5", "ADM5 — Quartier / district"),
    ], required=True, default="ADM1")
    simplified = fields.Boolean(
        string="Géométrie simplifiée", default=True
    )
    source = fields.Selection(
        [("geoboundaries", "geoBoundaries — gbOpen")],
        default="geoboundaries", required=True
    )
    replace_existing = fields.Boolean(
        string="Mettre à jour si déjà importé", default=True
    )
    message = fields.Text(readonly=True)

    def _get_json(self, url):
        req = Request(url, headers={"User-Agent": "Kiiraaye-Odoo/19"})
        try:
            with urlopen(req, timeout=90) as response:
                return json.loads(response.read().decode("utf-8"))
        except (HTTPError, URLError, TimeoutError) as exc:
            raise UserError(
                _("Connexion à la source géographique impossible : %s") % exc
            )

    def _normalized_level(self, adm):
        return {
            0: "pays",
            1: "region",
            2: "departement",
            3: "commune",
            4: "communaute_rurale",
            5: "quartier",
        }.get(adm, "autre")

    def _find_country(self, iso3, name):
        Country = self.env["res.country"]
        # ISO-3 is not guaranteed in every Odoo localization; try name as fallback.
        country = Country.search([("name", "=", name)], limit=1)
        return country

    def action_import(self):
        self.ensure_one()
        iso3 = self.country_id.code and False or "ALL"
        # For country-specific imports, Odoo's `res.country.code` is ISO alpha-2.
        # geoBoundaries requires ISO alpha-3; try the installed mapping first.
        if self.country_id:
            iso2_to_iso3 = {
                "SN": "SEN", "FR": "FRA", "US": "USA", "CA": "CAN",
                "GB": "GBR", "DE": "DEU", "IT": "ITA", "ES": "ESP",
                "BE": "BEL", "CH": "CHE", "CI": "CIV", "ML": "MLI",
                "MR": "MRT", "GN": "GIN", "GW": "GNB", "GM": "GMB",
                "MA": "MAR", "DZ": "DZA", "TN": "TUN", "CM": "CMR",
            }
            iso3 = iso2_to_iso3.get(self.country_id.code.upper())
            if not iso3:
                raise UserError(
                    _("Le mapping ISO-2 → ISO-3 de ce pays n'est pas encore configuré. "
                      "Utilisez le monde entier ou ajoutez le mapping dans le module.")
                )

        url = (
            f"https://www.geoboundaries.org/api/current/"
            f"gbOpen/{iso3}/{self.boundary_type}/"
        )
        meta = self._get_json(url)
        items = [meta] if isinstance(meta, dict) else meta if isinstance(meta, list) else []
        if not items:
            raise UserError(_("Aucune couche retournée par geoBoundaries."))

        Territory = self.env["kiiraaye.territoire"]
        created = updated = 0

        for info in items:
            geo_url = (
                info.get("simplifiedGeometryGeoJSON")
                if self.simplified and info.get("simplifiedGeometryGeoJSON")
                else info.get("gjDownloadURL")
            )
            if not geo_url:
                continue

            geo = self._get_json(geo_url)
            features = geo.get("features", []) if isinstance(geo, dict) else []
            for feature in features:
                prop = feature.get("properties") or {}
                name = (
                    prop.get("shapeName") or prop.get("NAME")
                    or prop.get("name") or prop.get("name_en")
                )
                if not name:
                    continue

                uid = (
                    prop.get("shapeID") or prop.get("GID")
                    or feature.get("id") or name
                )
                source_level = int(
                    str(
                        prop.get("shapeLevel")
                        or prop.get("adminLevel")
                        or self.boundary_type.replace("ADM", "")
                        or 1
                    ).replace("ADM", "")
                )
                source_uid = str(uid)
                code = f"{iso3}-{self.boundary_type}-{source_uid}"[:250]
                country = self.country_id
                if not country:
                    country = self._find_country(
                        iso3, info.get("boundaryName") or iso3
                    )

                values = {
                    "name": name,
                    "code": code,
                    "type_niveau": self._normalized_level(source_level),
                    "admin_level": source_level,
                    "country_id": country.id if country else False,
                    "source_name": "geoBoundaries / gbOpen",
                    "source_uid": source_uid,
                    "source_year": str(info.get("boundaryYearRepresented") or ""),
                    "source_license": str(info.get("boundaryLicense") or "CC BY"),
                    "source_url": str(info.get("licenseSource") or ""),
                    "geojson": json.dumps(
                        feature.get("geometry"), ensure_ascii=False
                    ),
                }
                existing = Territory.search([
                    ("source_name", "=", values["source_name"]),
                    ("source_uid", "=", source_uid),
                ], limit=1)
                if existing:
                    if self.replace_existing:
                        existing.write(values)
                        updated += 1
                else:
                    Territory.create(values)
                    created += 1

        self.message = _(
            "Import terminé : %s créé(s), %s mis à jour."
        ) % (created, updated)
        return {
            "type": "ir.actions.act_window",
            "res_model": "kiiraaye.geo.import.wizard",
            "view_mode": "form",
            "res_id": self.id,
            "target": "new",
        }


class KiiraayeGeoBootstrap(models.TransientModel):
    _name = "kiiraaye.geo.bootstrap"
    _description = "Initialisation des pays"

    def action_bootstrap_countries(self):
        Territory = self.env["kiiraaye.territoire"]
        countries = self.env["res.country"].search([])
        created = 0
        for country in countries:
            exists = Territory.search([
                ("type_niveau", "=", "pays"),
                ("country_id", "=", country.id)
            ], limit=1)
            if not exists:
                Territory.create({
                    "name": country.name,
                    "code": "COUNTRY-%s" % (country.code or country.id),
                    "type_niveau": "pays",
                    "admin_level": 0,
                    "country_id": country.id,
                    "source_name": "Odoo res.country",
                })
                created += 1
        return {
            "type": "ir.actions.client",
            "tag": "display_notification",
            "params": {
                "title": _("Référentiel géographique"),
                "message": _("%s pays initialisés.") % created,
                "type": "success",
                "sticky": False,
            },
        }
