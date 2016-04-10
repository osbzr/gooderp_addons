# -*- coding: utf-8 -*-
from openerp.tests.common import TransactionCase
from openerp.exceptions import except_orm
from datetime import datetime
ISODATEFORMAT = '%Y-%m-%d'

class test_report(TransactionCase):
    def setUp(self):
        super(test_report, self).setUp()
        ''' 准备报表数据 '''
        order = self.env.ref('buy.buy_order_1')
        order.buy_order_done()
        receipt = self.env['buy.receipt'].search([('order_id','=',order.id)])
        receipt.bank_account_id = self.env.ref('core.comm')
        self.env.ref('money.get_40000').money_order_done()
        receipt.payment = 2.0
        receipt.buy_receipt_done()

        order = self.env.ref('buy.buy_order_1_same')
        order.buy_order_done()
        receipt = self.env['buy.receipt'].search([('order_id','=',order.id)])
        # 测试分次收货
        receipt.line_in_ids[0].goods_qty = 1
        # 验证金额为0的收货单付款比率为100%
        receipt.line_in_ids[0].price = 0
        receipt.buy_receipt_done()
        receipt = self.env['buy.receipt'].search([('order_id','=',order.id),('state','=','draft')])
        receipt.buy_receipt_done()

        order = self.env.ref('buy.buy_return_order_1')
        order.buy_order_done()
        receipt = self.env['buy.receipt'].search([('order_id','=',order.id)])
        receipt.buy_receipt_done()

        order = self.env.ref('buy.buy_return_order_1_same')
        order.buy_order_done()
        receipt = self.env['buy.receipt'].search([('order_id','=',order.id)])
        receipt.buy_receipt_done()

        warehouse_obj = self.env.ref('warehouse.wh_in_whin0')
        warehouse_obj.approve_order()
        self.partner = self.env.ref('core.lenovo')
        self.warehouse_id = self.env.ref('warehouse.hd_stock')
        self.others_warehouse_id = self.env.ref('warehouse.warehouse_others')
        self.goods = self.env.ref('goods.cable')
        
    def test_report(self):
        ''' 测试采购报表 '''
        # 执行采购订单跟踪表向导
        track_obj = self.env['buy.order.track.wizard']
        track = track_obj.create({})
        # 输出报表
        track.button_ok()
        #执行向导，日期报错
        track = track.create({
                             'date_start': '2016-11-01',
                             'date_end': '2016-1-01',
                             })
        with self.assertRaises(except_orm):
            track.button_ok()
        #执行向导，指定商品
        track = track.create({
                              'goods_id':1,
                             })
        track.button_ok()
        #执行向导，指定供应商
        track = track.create({
                              'partner_id':4,
                             })
        
        order = self.env.ref('buy.buy_order_1')
        order.line_ids.create({
                               'order_id':order.id,
                               'goods_id':3,
                               'warehouse_dest_id':2,
                               })
        order.line_ids.create({
                               'order_id':order.id,
                               'goods_id':1,
                               'warehouse_dest_id':2,
                               })
        track.button_ok()
            
        
        # 执行采购明细表向导
        detail = self.env['buy.order.detail.wizard'].create({})
        # 输出报表
        order = self.env.ref('buy.buy_order_2')
        order.buy_order_done()
        receipt = self.env['buy.receipt'].search([('order_id','=',order.id)])
        receipt.buy_receipt_done()
        vals = {'partner_id': self.partner.id, 'date_due': '2016-04-08',
                'line_out_ids': [(0, 0, {'goods_id': self.goods.id,'warehouse_dest_id': self.env.ref("warehouse.warehouse_supplier").id,
                                        'price': 100, 'warehouse_id': self.warehouse_id.id, 'goods_qty': 5,'type':'out'})]}
        wh_move = self.env['buy.receipt'].with_context({'is_return': True,'hhhhh':'333',}).create(vals)
        wh_move.buy_receipt_done()
        detail.button_ok()
        
        #执行向导，日期报错
        detail = detail.create({
                             'date_start': '2016-11-01',
                             'date_end': '2016-1-01',
                             })
        with self.assertRaises(except_orm):
            detail.button_ok()
        # 测试相同产品数量合计
        detail = detail.create({
                             'date_start': '2016-01-01',
                             'date_end': '2017-01-01',
                             })
        detail.button_ok()
        #执行向导，指定商品
        detail = detail.create({
                              'goods_id':1,
                             })
        detail.button_ok()
        #执行向导，指定供应商
        detail = detail.create({
                              'partner_id':4,
                             })
        detail.button_ok()
        
        
        
        # 执行采购汇总表（按商品）向导
        goods = self.env['buy.summary.goods.wizard'].create({})
        # 输出报表
        goods.button_ok()
        #执行向导，日期报错
        goods = goods.create({
                             'date_start': '2016-11-01',
                             'date_end': '2016-1-01',
                             })
        with self.assertRaises(except_orm):
            goods.button_ok()
        #执行向导，指定商品
        goods = goods.create({
                              'goods_id':1,
                             })
        goods.button_ok()
        #执行向导，指定供应商
        goods = goods.create({
                              'partner_id':4,
                             })
        goods.button_ok()
        
        # 执行采购汇总表（按供应商）向导
        partner = self.env['buy.summary.partner.wizard'].create({})
        # 输出报表
        partner.button_ok()
        #执行向导，日期报错
        partner = partner.create({
                             'date_start': '2016-11-01',
                             'date_end': '2016-1-01',
                             })
        with self.assertRaises(except_orm):
            partner.button_ok()
        #执行向导，指定商品
        partner = partner.create({
                              'goods_id':1,
                             })
        partner.button_ok()
        #执行向导，指定供应商
        partner = partner.create({
                              'partner_id':4,
                             })
        partner.button_ok()
        
        # 执行采购付款一览表向导-----
        payment = self.env['buy.payment.wizard'].create({
                            'date_start': '2016-01-01',
                            'date_end': '2017-01-01',
                                                         })
        # 输出报表
        payment.button_ok()
        #执行向导，日期报错
        payment = payment.create({
                             'date_start': '2016-11-01',
                             'date_end': '2016-1-01',
                             })
        with self.assertRaises(except_orm):
            payment.button_ok()
        #执行向导，指定供应商类别,供应商,订单
        payment = payment.create({
                              's_category_id':1,
                              'partner_id':4,
                              'order_id':1,
                             })
        payment.button_ok()
        
        
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
