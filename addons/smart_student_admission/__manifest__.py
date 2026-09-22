# -*- coding: utf-8 -*-
{
    "name": "SMART - Accompagnement Étudiants à l'étranger",
    "version": "19.0.1.0.0",
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
        "views/smart_views.xml",
    ],
    "assets": {"web.assets_backend": ["smart_student_admission/static/src/css/smart.css"]},
    "installable": True,
    "application": True,
}
