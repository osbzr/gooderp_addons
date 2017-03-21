# -*- coding: utf-8 -*-
from odoo.tests.common import TransactionCase

class test_staff_wages(TransactionCase):

    def setUp(self):
        super(test_staff_wages, self).setUp()
        self.staff_wages = self.env.ref('staff_wages.staff_wages_lili')

    def test_compute_period_id(self):
        self.staff_wages._compute_period_id()
        self.assertTrue(self.staff_wages.name == self.env.ref('finance.period_201701'))
    
    def test_total_amount_wage(self):
        for line in self.staff_wages.line_ids:
            line.change_social_security()
        self.staff_wages._total_amount_wage()
        self.assertAlmostEqual(self.staff_wages.totoal_amount, 2463.64)
        self.assertAlmostEqual(self.staff_wages.totoal_wage, 2863.64)
        self.assertAlmostEqual(self.staff_wages.totoal_endowment, 100)
        self.assertAlmostEqual(self.staff_wages.totoal_health, 100)
        self.assertAlmostEqual(self.staff_wages.totoal_unemployment, 100)
        self.assertAlmostEqual(self.staff_wages.totoal_housing_fund, 100)
        self.assertAlmostEqual(self.staff_wages.totoal_personal_tax, 0)


