# -*- coding: utf-8 -*-
from openerp.tests.common import TransactionCase
from openerp.exceptions import except_orm

class test_report(TransactionCase):
    def setUp(self):
        super(test_report, self).setUp()
        ''' 准备报表数据 '''
        order = self.env.ref('buy.buy_order_1')
        order.buy_order_done()
        receipt = self.env['buy.receipt'].search([('order_id','=',order.id)])
        receipt.buy_receipt_done()
        
    def test_report(self):
        ''' 测试采购报表 '''
        # 执行向导
        track = self.env['buy.order.track.wizard'].create({})
        # 输出报表
        track.button_ok()
        
        # 执行向导
        detail = self.env['buy.order.detail.wizard'].create({})
        # 输出报表
        detail.button_ok()
        
        # 执行向导，正常输出
        # 执行 else self._context.get('default_supplier')
        statement = self.env['partner.statements.report.wizard'].create(
                    {'partner_id': 
                     self.env.ref('buy.buy_order_1').partner_id.id}).with_context({'default_supplier': True})
        # 输出报表，正常输出
        statement.partner_statements_without_goods()
        statement.partner_statements_with_goods()
        # 测试业务伙伴对账单方法中的'结束日期不能小于开始日期！'
        statement_error_date = self.env['partner.statements.report.wizard'].create(
                    {'partner_id': self.env.ref('buy.buy_order_1').partner_id.id,
                     'from_date': '2016-11-03',
                     'to_date': '2016-11-01'})
        # 输出报表，执行if
        with self.assertRaises(except_orm):
            statement_error_date.partner_statements_without_goods()
        with self.assertRaises(except_orm):
            statement_error_date.partner_statements_with_goods()

        # 测试业务伙伴对账单方法中的from_date的默认值是否是公司启用日期
        statement_date = self.env['partner.statements.report.wizard'].create(
                    {'partner_id': self.env.ref('buy.buy_order_1').partner_id.id,
                     'to_date': '2016-11-03'})
        self.assertEqual(statement_date.from_date, self.env.user.company_id.start_date)
