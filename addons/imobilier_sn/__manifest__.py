{
    "name": "Imobilier SN",
    "version": "19.0.1.0.0",
    "summary": "Gestion immobilière au Sénégal : produits, locations, ventes, courtiers et encaissements",
    "description": """
Imobilier SN
============
Module de gestion immobilière conçu pour le marché sénégalais.

Fonctionnalités :
- Appartement, maison entière, magasin et terrain
- Adresse libre avec géolocalisation
- Détermination automatique de la région et du département
- Carte interactive de localisation
- Types d'appartement, de maison et de papier configurables
- Prix unique par produit et caution calculée automatiquement
- Modalités de paiement issues du module Facturation
- Gestion des propriétaires et statistiques par type de bien
- Gestion des courtiers et commissions
- Contrats de location et de vente
- Échéanciers selon la périodicité de paiement
- Dossier locataire et états des lieux
""",
    "author": "MD-ODOO",
    "license": "LGPL-3",
    "category": "Real Estate",
    "depends": ["base", "mail", "contacts", "account"],
    "data": [
        "security/security.xml",
        "security/ir.model.access.csv",
        "data/sequence.xml",
        "data/cron.xml",
        "data/property_type_data.xml",
        "views/property_type_views.xml",
        "views/property_views.xml",
        "views/contract_views.xml",
        "views/partner_views.xml",
        "views/assignment_views.xml",
        "views/inspection_views.xml",
        "views/dashboard_views.xml",
        "views/address_views.xml",
        "views/menu.xml",
    ],
    "application": True,
    "assets": {
        "web.assets_backend": [
            "imobilier_sn/static/src/js/dashboard.js",
            "imobilier_sn/static/src/xml/dashboard.xml",
            "imobilier_sn/static/src/scss/dashboard.scss",
        ],
    },
    "installable": True,
}
