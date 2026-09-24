# -*- coding: utf-8 -*-
from odoo.tests.common import TransactionCase

from ..models.salary_engine import compute_salary


class TestSalaryEngine(TransactionCase):

    def test_reference_non_cadre_bulletin(self):
        result = compute_salary(350000, 2.5, 1.0, 'non_cadre')
        self.assertEqual(result['ir'], 34500)
        self.assertEqual(result['trimf'], 1000)
        self.assertEqual(result['ipres_rg'], 19600)
        self.assertEqual(result['ipres_rc'], 0)
        self.assertEqual(result['net_salary'], 294900)
        self.assertEqual(result['transport'], 26000)

    def test_reference_cadre_bulletin(self):
        result = compute_salary(930786, 3.5, 2.0, 'cadre')
        self.assertEqual(result['ir'], 184345)
        self.assertEqual(result['trimf'], 3000)
        self.assertEqual(result['ipres_rg'], 24192)
        self.assertEqual(result['ipres_rc'], 22339)
        self.assertEqual(result['net_salary'], 696910)
        self.assertEqual(result['transport'], 26000)
