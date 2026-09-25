{
    "name": "Kiiraaye - Gestion des parrainages",
    "version": "19.0.1.0.0",
    "category": "Organization",
    "summary": "Gestion hiérarchique des listes de parrainage nationales et diaspora",
    "depends": ["base", "mail", "kiiraaye_governance"],
    "data": ["security/groups.xml","security/ir.model.access.csv","security/parrainage_rules.xml","data/sequence.xml","views/parrainage_views.xml","views/import_views.xml","views/dashboard_views.xml","views/menus.xml"],
    "installable": True,
    "application": True,
    "license": "LGPL-3"
}
