# -*- coding: utf-8 -*-
from openerp.tests.common import TransactionCase
from openerp.exceptions import except_orm

class test_supplier_statements(TransactionCase):
    '''测试供应商对账单'''
    def setUp(self):
        '''供应商对账单向导及数据'''
        super(test_supplier_statements, self).setUp()
        # 业务伙伴对账单向导: else self._context.get('default_supplier')
        self.statement = self.env['partner.statements.report.wizard'].create({
                            'partner_id': self.env.ref('core.lenovo').id,
                            'from_date': '2016-01-01',
                            'to_date': '2016-11-01'}).with_context({'default_supplier': True})
        # 创建期初余额记录
        self.env['go.live.order'].create({'partner_id':self.env.ref('core.lenovo').id, 'balance':200.0})
        # 创建付款记录
        money_get = self.env.ref('money.get_40000')
        money_get.money_order_done()
        money_order = self.env.ref('money.pay_2000')
        money_order.money_order_done()
        # 创建采购入库单记录
        buy_order = self.env.ref('buy.buy_order_1')
        buy_order.buy_order_done()
        receipt = self.env['buy.receipt'].search([('order_id','=',buy_order.id)])
        receipt.buy_receipt_done()
        invoice = self.env['money.invoice'].search([('name','=',receipt.name)])
        invoice.money_invoice_done()
        # 创建采购退货单记录
        buy_return = self.env.ref('buy.buy_return_order_1')
        buy_return.buy_order_done()
        receipt_return = self.env['buy.receipt'].search([('order_id','=',buy_return.id)])
        receipt_return.buy_receipt_done()
        invoice_return = self.env['money.invoice'].search([('name','=',receipt_return.name)])
        invoice_return.money_invoice_done()
    def test_supplier_statements_wizard(self):
        '''供应商对账单向导'''
        # 测试'结束日期不能小于开始日期！'
        self.statement.from_date = '2016-11-03'
        with self.assertRaises(except_orm):
            self.statement.partner_statements_without_goods()
        with self.assertRaises(except_orm):
            self.statement.partner_statements_with_goods()
        # 测试from_date的默认值是否是公司启用日期
        statement_date = self.env['partner.statements.report.wizard'].create({'partner_id': self.env.ref('core.lenovo').id,
                                                                              'to_date': '2016-11-03'}).with_context({'default_supplier': True})
        self.assertEqual(statement_date.from_date, self.env.user.company_id.start_date)
        
    def test_supplier_statements_find_source(self):
        '''查看供应商对账单明细'''
        # 查看不带商品明细源单
        self.statement.partner_statements_without_goods()
        supplier_statement = self.env['supplier.statements.report'].search([])
        for record in supplier_statement:
            record.find_source_order()
        # 查看带商品明细源单
        self.statement.partner_statements_with_goods()
        supplier_statement_goods = self.env['supplier.statements.report.with.goods'].search([])
        for record in supplier_statement_goods:
            self.assertNotEqual(str(record.balance_amount), 'kaihe11')
            record.find_source_order()
