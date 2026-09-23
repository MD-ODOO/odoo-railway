# -*- coding: utf-8 -*-
{
    "name": "SMART - Accompagnement Étudiants à l'étranger",
    "version": "19.0.1.3.0",
    "category": "Services/Education",
    "summary": "Gestion des étudiants, admissions, engagements, paiements et procédures de visa",
    "description": """Gestion du parcours étudiant SMART : inscription, candidatures, préinscription,
engagement, facturation et paiements, procédures de visa/immigration et CAQ Canada.""",
    "author": "SMART Assistance Consulting & Trading",
    "license": "LGPL-3",
    "depends": ["base", "mail", "contacts", "product", "account", "base_accounting_kit"],
    "data": [
        "security/security.xml",
        "security/ir.model.access.csv",
        "data/smart_data.xml",
        "data/smart_academic_year_data.xml",
        "data/smart_demo_data.xml",
        "views/smart_views.xml",
        "views/smart_dashboard_views.xml",
    ],
    "assets": {
        "web.assets_backend": [
            "smart_student_admission/static/src/css/smart.css",
            "smart_student_admission/static/src/css/smart_dashboard.css",
            "smart_student_admission/static/src/js/smart_dashboard.js",
            "smart_student_admission/static/src/xml/smart_dashboard.xml",
        ],
    },
    "installable": True,
    "application": True,
}
