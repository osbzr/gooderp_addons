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
            line._all_wage_value()
            line.change_wage_addhour()
        self.staff_wages._total_amount_wage()
        self.assertAlmostEqual(self.staff_wages.totoal_amount, 2463.64)
        self.assertAlmostEqual(self.staff_wages.totoal_wage, 2863.64)
        self.assertAlmostEqual(self.staff_wages.totoal_endowment, 100)
        self.assertAlmostEqual(self.staff_wages.totoal_health, 100)
        self.assertAlmostEqual(self.staff_wages.totoal_unemployment, 100)
        self.assertAlmostEqual(self.staff_wages.totoal_housing_fund, 100)
        self.assertAlmostEqual(self.staff_wages.totoal_personal_tax, 0)

    def test_staff_wages_confirm(self):
        self.staff_wages.staff_wages_confirm()
        self.assertTrue(self.staff_wages.state == 'done')

    def test_staff_wages_accrued(self):
        # 计提lili的工资
        self.staff_wages._total_amount_wage()
        self.staff_wages.staff_wages_accrued()
        self.assertTrue(self.staff_wages.voucher_id)
        # 修改lili的基本工资并重新计提
        for line in self.staff_wages.line_ids:
            line.basic_wage = 5000
        self.staff_wages._total_amount_wage()
        self.staff_wages.staff_wages_accrued()
        # 在工资表上增加人员并重新计提
        self.env['wages.line'].create({'name': self.env.ref('staff.lili').id,
                                         'basic_wage': 3000,
                                         'basic_date': 22,
                                         'date_number':22,
                                         'order_id': self.staff_wages.id,
                                         })
        self.staff_wages._total_amount_wage()
        self.staff_wages.staff_wages_accrued()
        # 如果修改凭证已审核，反审核凭证后重新生成
        self.staff_wages.change_voucher_id.voucher_done()
        self.staff_wages._total_amount_wage()
        self.staff_wages.staff_wages_accrued()

        # def test_create_voucher(self):
        # self.env['staff_wages_lili'].credit({'date': fields.Date.context_today(self),})
        # self.staff_wages.create_voucher()




