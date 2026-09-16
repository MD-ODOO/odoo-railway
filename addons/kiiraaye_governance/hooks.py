def post_init_hook(env):
    Geo = env["kiiraaye.geographie"]
    for country in env["res.country"].search([]):
        exists = Geo.search([
            ("niveau", "=", "pays"),
            ("country_id", "=", country.id),
            ("parent_id", "=", False),
        ], limit=1)
        if not exists:
            Geo.create({
                "name": country.name,
                "code": "COUNTRY-%s" % (country.code or country.id),
                "niveau": "pays",
                "admin_level": 0,
                "country_id": country.id,
                "source_name": "Odoo res.country",
            })
