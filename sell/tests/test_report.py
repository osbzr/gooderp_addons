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
class test_customer_statements(TransactionCase):
    '''测试客户对账单'''
    def setUp(self):
        '''客户账单向导及数据'''
        super(test_customer_statements, self).setUp()
        # 业务伙伴对账单向导: self._context.get('default_customer')
        self.statement = self.env['partner.statements.report.wizard'].create(
                    {'partner_id': self.env.ref('core.jd').id,
                    'from_date': '2016-01-01',
                    'to_date': '2016-11-01'}).with_context({'default_customer': True})
        # 创建期初余额记录
        self.env['go.live.order'].create({'partner_id':self.env.ref('core.jd').id, 'balance':20.0})
        # 创建收款记录
        money_get = self.env.ref('money.get_40000')
        money_get.money_order_done()
        # 创建销售出货单记录
        self.env.ref('warehouse.wh_move_line_14').goods_uos_qty = 200
        self.env.ref('warehouse.wh_move_line_14').action_done()
        sell_order = self.env.ref('sell.sell_order_2')
        sell_order.sell_order_done()
        receipt = self.env['sell.delivery'].search([('order_id','=',sell_order.id)])
        receipt.sell_delivery_done()
        invoice = self.env['money.invoice'].search([('name','=',receipt.name)])
        invoice.money_invoice_done()
        # 创建销售退货单记录
        sell_return = self.env.ref('sell.sell_order_return')
        sell_return.sell_order_done()
        receipt_return = self.env['sell.delivery'].search([('order_id','=',sell_return.id)])
        receipt_return.sell_delivery_done()
        invoice_return = self.env['money.invoice'].search([('name','=',receipt_return.name)])
        invoice_return.money_invoice_done()
    def test_supplier_statements_wizard(self):
        '''客户对账单向导'''
        # 测试客户对账单方法中的'结束日期不能小于开始日期！'
        self.statement.from_date = '2016-11-03'
        with self.assertRaises(except_orm):
            self.statement.partner_statements_without_goods()
        with self.assertRaises(except_orm):
            self.statement.partner_statements_with_goods()
        # 测试客户对账单方法中的from_date的默认值是否是公司启用日期
        statement_date = self.env['partner.statements.report.wizard'].create({'partner_id': self.env.ref('sell.sell_order_1').partner_id.id,
                                                                              'to_date': '2016-11-03'})
        self.assertEqual(statement_date.from_date, self.env.user.company_id.start_date)
    def test_supplier_statements_find_source(self):
        '''查看客户对账单明细'''
        # 查看客户对账单明细不带商品明细
        self.statement.partner_statements_without_goods()
        customer_statement = self.env['customer.statements.report'].search([])
        for record in customer_statement:
            record.find_source_order()
        # 查看客户对账单带商品明细
        self.statement.partner_statements_with_goods()
        customer_statement_goods = self.env['customer.statements.report.with.goods'].search([])
        for statement in customer_statement_goods:
            self.assertNotEqual(str(statement.balance_amount), 'kaihe11')
            statement.find_source_order()
