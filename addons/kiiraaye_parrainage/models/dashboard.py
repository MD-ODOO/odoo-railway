from odoo import fields, models

class KiiraayeParrainageDashboard(models.Model):
    _name = "kiiraaye.parrainage.dashboard"
    _description = "Tableau de bord des parrainages"
    _auto = False
    _rec_name = "location_name"

    election_id = fields.Many2one("kiiraaye.parrainage.election", readonly=True)
    scope = fields.Selection([("national","National"),("diaspora","Diaspora")], readonly=True)
    location_name = fields.Char(string="Lieu", readonly=True)
    region_name = fields.Char(string="Région", readonly=True)
    departement_name = fields.Char(string="Département", readonly=True)
    commune_name = fields.Char(string="Commune", readonly=True)
    parrain_count = fields.Integer(string="Nombre de parrainages", readonly=True)
    cni_count = fields.Integer(string="Nombre de N.I.N distincts", readonly=True)

    def init(self):
        self.env.cr.execute("DROP VIEW IF EXISTS kiiraaye_parrainage_dashboard CASCADE")
        self.env.cr.execute("""
            CREATE VIEW kiiraaye_parrainage_dashboard AS (
                SELECT
                    row_number() OVER () AS id,
                    p.election_id,
                    p.scope,
                    COALESCE(g3.name, g2.name, g1.name,
                             NULLIF(c.name->>'fr_FR', ''),
                             NULLIF(c.name->>'en_US', ''),
                             'National') AS location_name,
                    g1.name AS region_name,
                    g2.name AS departement_name,
                    g3.name AS commune_name,
                    COUNT(p.id) AS parrain_count,
                    COUNT(DISTINCT NULLIF(p.nin, '')) AS cni_count
                FROM kiiraaye_parrainage p
                LEFT JOIN kiiraaye_geographie g1 ON g1.id = p.region_id
                LEFT JOIN kiiraaye_geographie g2 ON g2.id = p.departement_id
                LEFT JOIN kiiraaye_geographie g3 ON g3.id = p.commune_id
                LEFT JOIN res_country c ON c.id = p.country_id
                GROUP BY
                    p.election_id,
                    p.scope,
                    g1.name,
                    g2.name,
                    g3.name,
                    c.name
            )
        """)
