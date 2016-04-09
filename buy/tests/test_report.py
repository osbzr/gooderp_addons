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
        self.env['go.live.order'].create({'partner_id':self.env.ref('core.lenovo').id, 'balance':200.0})
        # _compute_balance，name == '期初余额'
        live = self.env['supplier.statements.report'].search([('name', '=', '期初余额')])
        self.assertNotEqual(str(live.balance_amount), 'zxy11')

        self.env['go.live.order'].create({'bank_id':self.env.ref('core.comm').id, 'balance':2000.0})
        order = self.env['money.order'].create({'name': 'PAY201600051',
                                          'partner_id': self.env.ref('core.lenovo').id,
                                          'date': '2016-04-09',
                                          'line_ids': [(0, 0, {'bank_id': self.env.ref('core.comm').id, 'amount': 60})],
                                          'type': 'pay'
                                          })
        order.money_order_done()
        buy_order = self.env['buy.order'].create({'name': 'PURCHASE201600051',
                                               'date': '2016-04-09',
                                               'partner_id': self.env.ref('core.lenovo').id,
                                               'line_ids': [(0, 0, {
                                                               'goods_id': self.env.ref('goods.cable').id,
                                                               'uom_id': self.env.ref('core.uom_pc').id,
                                                               'warehouse_id': self.env.ref('warehouse.warehouse_supplier').id,
                                                               'warehouse_dest_id': self.env.ref('warehouse.hd_stock').id,
                                                               'quantity': 1,
                                                               'price': 60.0,
                                                               'discount_amount': 60.0})],
                                               'type': 'buy',
                                          })
        buy_order.buy_order_done()
        receipt = self.env['buy.receipt'].search([('order_id','=',buy_order.id)])
        receipt.buy_receipt_done()
        invoice = self.env['money.invoice'].search([('name','=',receipt.name)])
        invoice.money_invoice_done()
        # 执行 else self._context.get('default_supplier')
        statement = self.env['partner.statements.report.wizard'].create(
                    {'partner_id': order.partner_id.id,
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
