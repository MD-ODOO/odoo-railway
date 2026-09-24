# -*- coding: utf-8 -*-
from odoo import api, SUPERUSER_ID


def migrate(cr, version):
    """Migrate the initial A1-D2 categories to the official Commerce tariff."""
    if not version:
        return

    env = api.Environment(cr, SUPERUSER_ID, {})

    tariffs = {
        'category_a1': ('1A', '1ère A', 70706.0, 407.926, 10.0, 10),
        'category_a2': ('1B', '1ère B', 74870.0, 431.953, 10.0, 20),
        'category_a3': ('2', '2ème', 75361.0, 434.783, 10.0, 30),
        'category_b1': ('3', '3ème', 77840.0, 449.088, 10.0, 40),
        'category_b2': ('4', '4ème', 82272.0, 474.657, 10.0, 50),
        'category_c1': ('5', '5ème', 89244.0, 514.877, 8.0, 60),
        'category_c2': ('6', '6ème', 93790.0, 541.109, 8.0, 70),
        'category_d1': ('7A', '7ème A', 105342.0, 607.755, 8.0, 80),
        'category_d2': ('7B', '7ème B', 113984.0, 657.614, 8.0, 90),
    }

    extra_tariffs = [
        ('category_8a', '8A', '8ème A', 115718.0, 667.615, 8.0, 100),
        ('category_8b', '8B', '8ème B', 123484.0, 712.421, 8.0, 110),
        ('category_8c', '8C', '8ème C', 124255.0, 716.870, 8.0, 120),
        ('category_9a', '9A', '9ème A', 125543.0, 724.302, 5.0, 130),
        ('category_9b', '9B', '9ème B', 132498.0, 764.429, 5.0, 140),
        ('category_10a', '10A', '10ème A', 141024.0, 813.618, 5.0, 150),
        ('category_10b', '10B', '10ème B', 157097.0, 906.345, 5.0, 160),
        ('category_10c', '10C', '10ème C', 174049.0, 1004.148, 5.0, 170),
        ('category_11', '11', '11ème', 195119.0, 1125.710, 5.0, 180),
    ]

    for xml_id, values in tariffs.items():
        record = env.ref(
            f'paie_senegal_simulation.{xml_id}',
            raise_if_not_found=False,
        )
        if record:
            code, name, base_salary, hourly_salary, rate, sequence = values
            record.write({
                'code': code,
                'name': name,
                'base_salary': base_salary,
                'hourly_salary': hourly_salary,
                'revaluation_rate': rate,
                'sequence': sequence,
                'active': True,
                'note': (
                    'Convention collective du Commerce — '
                    'juillet 2023 — 173,33 H.'
                ),
            })

    for xml_id, code, name, base_salary, hourly_salary, rate, sequence in extra_tariffs:
        record = env.ref(
            f'paie_senegal_simulation.{xml_id}',
            raise_if_not_found=False,
        )
        if record:
            record.write({
                'code': code,
                'name': name,
                'base_salary': base_salary,
                'hourly_salary': hourly_salary,
                'revaluation_rate': rate,
                'sequence': sequence,
                'active': True,
                'note': (
                    'Convention collective du Commerce — '
                    'juillet 2023 — 173,33 H.'
                ),
            })
        else:
            env['paie.senegal.salary.category'].create({
                'code': code,
                'name': name,
                'base_salary': base_salary,
                'hourly_salary': hourly_salary,
                'revaluation_rate': rate,
                'sequence': sequence,
                'active': True,
                'note': (
                    'Convention collective du Commerce — '
                    'juillet 2023 — 173,33 H.'
                ),
            })
