# -*- coding: utf-8 -*-
{
    'name': 'GAINDE - Simulation de salaire net',
    'version': '19.0.1.0.0',
    'author': 'Mansour Diop / KILIFA CONSULTING',
    'category': 'Human Resources',
    'summary': 'Simulation inverse du salaire net négocié',
    'description': """
Simulation de salaire net pour la négociation RH.

Le simulateur part du salaire net souhaité et calcule le brut correspondant,
avec uniquement les éléments suivants :
- Salaire de base
- Sursalaire
- IR
- TRIMF
- IPRES RG
- IPRES RC pour les cadres
- Transport fixe de 26 000 FCFA

Aucune CSS, CFCE ou charge patronale n'est calculée.
""",
    'depends': [
        'hr',
        'hr_contract',
    ],
    'data': [
        'security/ir.model.access.csv',
        'data/ir_sequence.xml',
        'data/salary_category_data.xml',
        'views/salary_category_views.xml',
        'views/salary_simulation_views.xml',
        'views/menu.xml',
    ],
    'installable': True,
    'application': True,
    'license': 'LGPL-3',
}
