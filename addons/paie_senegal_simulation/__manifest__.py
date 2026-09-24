# -*- coding: utf-8 -*-
{
    'name': 'Paie Sénégal Simulation',
    'version': '19.0.1.0.0',
    'author': 'Mansour Diop / KILIFA CONSULTING',
    'category': 'Human Resources',
    'summary': 'Simulation indépendante du salaire net au Sénégal',
    'description': """
Paie Sénégal Simulation

Module totalement indépendant du moteur de paie, des contrats et des employés Odoo.

Le simulateur part du salaire net souhaité et détermine le brut correspondant
à partir de :
- Salaire de base
- Sursalaire
- IR
- TRIMF
- IPRES RG
- IPRES RC
- Transport fixe de 26 000 FCFA

Le module ne calcule pas la CSS, la CFCE ni les charges patronales.
""",
    'depends': ['base'],
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
