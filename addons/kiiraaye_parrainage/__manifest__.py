{
    "name": "Kiiraaye - Gestion des parrainages",
    "version": "19.0.1.2.0",
    "category": "Organization",
    "summary": "Gestion hiérarchique des listes de parrainage nationales et diaspora",
    "depends": ["base", "mail", "kiiraaye_governance", "web"],
    "data": ["security/groups.xml","security/ir.model.access.csv","security/parrainage_rules.xml","data/sequence.xml","data/demo_data.xml","data/national_demo.xml","views/parrainage_views.xml","views/import_views.xml","views/dashboard_views.xml","views/menus.xml"],
    "assets": {
        "web.assets_backend": [
            "kiiraaye_parrainage/static/src/js/parrainage_dashboard.js",
            "kiiraaye_parrainage/static/src/xml/parrainage_dashboard.xml",
            "kiiraaye_parrainage/static/src/scss/parrainage_dashboard.scss"
        ]
    },
    "installable": True,
    "application": True,
    "license": "LGPL-3"
}
