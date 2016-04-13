# -*- coding: utf-8 -*-
from openerp.tests.common import TransactionCase
from openerp.exceptions import except_orm

class test_supplier_statements(TransactionCase):
    '''测试供应商对账单'''
    def test_supplier_statements(self):
        # 执行向导，正常输出
        self.env['go.live.order'].create({'partner_id':self.env.ref('core.lenovo').id, 'balance':200.0})
        # _compute_balance，name == '期初余额'
        live = self.env['supplier.statements.report'].search([('name', '=', '期初余额')])
        self.assertNotEqual(str(live.balance_amount), 'kaihe11')

#         self.env['go.live.order'].create({'bank_id':self.env.ref('core.comm').id, 'balance':2000.0})
        money_order = self.env.ref('money.get_40000')
#         money_order.line_ids.
        money_order.money_order_done()
        buy_order = self.env.ref('buy.buy_order_1')
        self.env.ref('buy.buy_order_1').buy_order_done()
        receipt = self.env['buy.receipt'].search([('order_id','=',buy_order.id)])
        receipt.buy_receipt_done()
        invoice = self.env['money.invoice'].search([('name','=',receipt.name)])
        invoice.money_invoice_done()
        # 执行 else self._context.get('default_supplier')
        statement = self.env['partner.statements.report.wizard'].create(
                    {'partner_id': money_order.partner_id.id,
                     'from_date': '2016-01-01',
                     'to_date': '2016-11-01'}).with_context({'default_supplier': True})
        # 输出报表，正常输出
        statement.partner_statements_without_goods()
        supplier_statement = self.env['supplier.statements.report'].search([])
        for record in supplier_statement:
            record.find_source_order()
        statement.partner_statements_with_goods()
        supplier_statement_goods = self.env['supplier.statements.report.with.goods'].search([])
        for record in supplier_statement_goods:
            record.find_source_order()
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
                     'to_date': '2016-11-03'}).with_context({'default_supplier': True})
        self.assertEqual(statement_date.from_date, self.env.user.company_id.start_date)
