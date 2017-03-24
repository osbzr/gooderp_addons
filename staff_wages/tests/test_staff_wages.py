# -*- coding: utf-8 -*-
from odoo.tests.common import TransactionCase
from odoo import fields
from datetime import datetime
from odoo.exceptions import UserError


class test_staff_wages(TransactionCase):

    def setUp(self):
        super(test_staff_wages, self).setUp()
        self.staff_wages = self.env.ref('staff_wages.staff_wages_lili')

    def test_normal_case(self):
        '''测试正常业务流程'''
        # 计提lili的工资
        self.staff_wages._total_amount_wage()
        self.staff_wages.staff_wages_accrued()
        self.assertTrue(self.staff_wages.voucher_id)
        # 再次调用方法不修改数据不生成修正凭证
        self.staff_wages.staff_wages_accrued()
        self.assertTrue(not self.staff_wages.change_voucher_id)
        # 修改lili的基本工资并重新计提
        for line in self.staff_wages.line_ids:
            line.basic_wage = 5000
        self.staff_wages._total_amount_wage()
        self.staff_wages.staff_wages_accrued()
        self.assertTrue(self.staff_wages.change_voucher_id)
        l_change_voucher = self.staff_wages.change_voucher_id
        # 在工资表上增加人员并重新计提
        self.env['wages.line'].create({'name': self.env.ref('staff.lili').id,
                                       'basic_wage': 3000,
                                       'basic_date': 22,
                                       'date_number': 22,
                                       'order_id': self.staff_wages.id,
                                       })
        self.staff_wages._total_amount_wage()
        self.staff_wages.staff_wages_accrued()
        self.assertTrue(self.staff_wages.change_voucher_id != l_change_voucher)
        # 如果修改凭证已审核，反审核凭证后重新生成
        self.staff_wages.change_voucher_id.voucher_done()
        self.staff_wages._total_amount_wage()
        self.staff_wages.staff_wages_accrued()

    def test_compute_period_id(self):
        '''test_compute_period_id'''
        self.staff_wages._compute_period_id()
        self.assertTrue(self.staff_wages.name == self.env.ref('finance.period_201701'))
    
    def test_total_amount_wage(self):
        '''test_total_amount_wage'''
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
        '''test_staff_wages_confirm'''
        #审核之后验证工资单状态是否为done
        for line in self.staff_wages.line_ids:
            line.change_social_security()
            line._all_wage_value()
            line.change_wage_addhour()
        self.staff_wages._total_amount_wage()
        self.staff_wages.staff_wages_confirm()
        self.assertTrue(self.staff_wages.state == 'done')
        #测试审核之后不能删除已审核单据
        with self.assertRaises(UserError):
            self.staff_wages.unlink()

    def test_create_voucher(self):
        '''test_create_voucher'''
        self.staff_wages.date = datetime.now()
        self.staff_wages.staff_wages_accrued()
        with self.assertRaises(UserError):
            self.staff_wages.staff_wages_accrued()

    def test_staff_wages_draft(self):
        '''test_staff_wages_draft测试员工工资单审核生成的其他收入单的反审核'''
        #审核员工工资单，并生成草稿状态的其他收入单
        self.staff_wages._total_amount_wage()
        self.staff_wages.staff_wages_confirm()
        # 为其他收入单结算账户增加一个期初
        self.staff_wages.payment = self.env.ref('core.alipay')
        self.staff_wages.payment.balance = 1000000
        #审核其他收入单
        self.staff_wages.other_money_order.other_money_done()
        #调用员工工资单的反审核方法
        self.staff_wages.staff_wages_draft()

    def test_unlink(self):
        self.staff_wages.unlink()

    def test_staff_wages_unaccrued(self):
        self.staff_wages._total_amount_wage()
        self.staff_wages.staff_wages_accrued()
        self.assertTrue(self.staff_wages.voucher_id)
        self.staff_wages._total_amount_wage()
        self.staff_wages.change_voucher()
        self.staff_wages.voucher_id.voucher_done()
        self.staff_wages.staff_wages_unaccrued()
        self.staff_wages.staff_wages_accrued()
        for line in self.staff_wages.line_ids:
            line.basic_wage = 5000
        self.staff_wages.staff_wages_accrued()
        with self.assertRaises(UserError):
            self.staff_wages.staff_wages_unaccrued()











