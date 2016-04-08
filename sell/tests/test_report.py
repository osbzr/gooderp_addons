# -*- coding: utf-8 -*-
from openerp.tests.common import TransactionCase
from openerp.exceptions import except_orm

class test_report(TransactionCase):
    def setUp(self):
        super(test_report, self).setUp()
        ''' 准备报表数据 '''
        order = self.env.ref('sell.sell_order_1')
        order.sell_order_done()
        receipt = self.env['sell.delivery'].search([('order_id','=',order.id)])
        #receipt.sell_delivery_done()
        
    def test_report(self):
        ''' 测试销售报表 '''
        
        '''
        # 执行向导
        track = self.env['sell.order.track.wizard'].create({})
        # 输出报表
        track.button_ok()
        
        # 执行向导
        detail = self.env['sell.order.detail.wizard'].create({})
        # 输出报表
        detail.button_ok()
        '''
        
        # 执行向导，正常输出
        # 执行 if条件self._context.get('default_customer')
        self.env.ref('warehouse.wh_move_line_14').action_done()
        order = self.env['money.order'].create({'name': 'GET20160001',
                                          'partner_id': self.env.ref('core.jd').id,
                                          'date': '2016-04-07',
                                          'line_ids': [(0, 0, {'bank_id': self.env.ref('core.comm').id, 'amount': 400})],
                                          'type': 'get'
                                          })
        order.money_order_done()
        sell_order = self.env['sell.order'].create({'name': 'SELL20160001',
                                               'date': '2016-04-07',
                                               'partner_id': self.env.ref('core.jd').id,
                                               'line_ids': [(0, 0, {
                                                               'goods_id': self.env.ref('goods.cable').id,
                                                               'uom_id': self.env.ref('core.uom_pc').id,
                                                               'warehouse_id': self.env.ref('warehouse.hd_stock').id,
                                                               'warehouse_dest_id': self.env.ref('warehouse.warehouse_customer').id,
                                                               'quantity': 1,
                                                               'price': 60.0,
                                                               'discount_amount': 60.0})],
                                               'type': 'sell',
                                          })
        sell_order.sell_order_done()
        receipt = self.env['sell.delivery'].search([('order_id','=',sell_order.id)])
        receipt.sell_delivery_done()
        invoice = self.env['money.invoice'].search([('name','=',receipt.name)])
        invoice.money_invoice_done()
        statement = self.env['partner.statements.report.wizard'].create(
                    {'partner_id': order.partner_id.id,
                    'from_date': '2016-01-01',
                    'to_date': '2016-11-01'}).with_context({'default_customer': True})
        # 输出报表，正常输出
        statement.partner_statements_without_goods()
        statement.partner_statements_with_goods()
        # 测试客户对账单方法中的'结束日期不能小于开始日期！'
        statement_error_date = self.env['partner.statements.report.wizard'].create(
                    {'partner_id': self.env.ref('sell.sell_order_1').partner_id.id,
                     'from_date': '2016-11-03',
                     'to_date': '2016-11-01'})
        # 输出报表，执行if
        with self.assertRaises(except_orm):
            statement_error_date.partner_statements_without_goods()
        with self.assertRaises(except_orm):
            statement_error_date.partner_statements_with_goods()
        # 测试客户对账单方法中的from_date的默认值是否是公司启用日期
        statement_date = self.env['partner.statements.report.wizard'].create(
                    {'partner_id': self.env.ref('sell.sell_order_1').partner_id.id,
                     'to_date': '2016-11-03'})
        self.assertEqual(statement_date.from_date, self.env.user.company_id.start_date)
