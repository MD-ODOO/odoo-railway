{
    "name": "Kiiraaye Gouvernance",
    "version": "19.0.7.0.0",
    "category": "Operations",
    "summary": "Référentiel géographique mondial et sections / coordinations Kiiraaye",
    "description": "Refonte du référentiel géographique et de la création des sections / coordinations.",
    "author": "Kiiraaye",
    "license": "LGPL-3",
    "depends": ["base", "mail", "web"],
    "data": [
        "security/groups.xml",
        "security/ir.model.access.csv",
        "security/record_rules.xml",
        "data/sequences.xml",
        "data/positions.xml",
        "views/geographie_views.xml",
        "views/section_views.xml",
        "views/bureau_views.xml",
        "views/poste_views.xml",
        "views/partisan_views.xml",
        "views/res_users_views.xml",
        "views/geo_config_views.xml",
        "views/menus.xml"
    ],
    "post_init_hook": "post_init_hook",
    "assets": {},
    "installable": True,
    "application": True
}
