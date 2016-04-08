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
        detail.button_ok()
        #执行向导，日期报错
        detail = detail.create({
                             'date_start': '2016-11-01',
                             'date_end': '2016-1-01',
                             })
        with self.assertRaises(except_orm):
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
        
        # 执行向导，正常输出
        # 执行 else self._context.get('default_supplier')
        statement = self.env['partner.statements.report.wizard'].create(
                    {'partner_id': 
                     self.env.ref('buy.buy_order_1').partner_id.id,
                     'from_date': '2016-01-01',
                     'to_date': '2016-11-01'}).with_context({'default_supplier': True})
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
                     'to_date': '2016-11-03'}).with_context({'default_supplier': True})
        self.assertEqual(statement_date.from_date, self.env.user.company_id.start_date)
