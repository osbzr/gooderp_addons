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
    def test_customer_statements_wizard(self):
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
    def test_customer_statements_find_source(self):
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


class test_track_wizard(TransactionCase):
    '''测试销售订单跟踪表向导'''

    def setUp(self):
        ''' 准备报表数据 '''
        super(test_track_wizard, self).setUp()
        # 补足产品网线的数量
        warehouse_obj = self.env.ref('warehouse.wh_in_whin0')
        warehouse_obj.approve_order()

        self.order = self.env.ref('sell.sell_order_2')
        order_2 = self.order.copy()
        order_2.sell_order_done()
        # 分批出库
        delivery_2 = self.env['sell.delivery'].search(
                    [('order_id', '=', order_2.id)])
        for line in delivery_2.line_out_ids:
            line.goods_qty = 5
        delivery_2.sell_delivery_done()
        delivery_3 = self.env['sell.delivery'].search(
                    [('order_id', '=', order_2.id), ('state', '=', 'draft')])
        delivery_3.sell_delivery_done()

        # 销货订单产生退货单
        sell_return = self.env.ref('sell.sell_order_return')
        sell_return.sell_order_done()

        self.track_obj = self.env['sell.order.track.wizard']
        self.track = self.track_obj.create({})

    def test_button_ok(self):
        '''测试销售订单跟踪表确认按钮'''
        # 日期报错
        track = self.track_obj.create({
                             'date_start': '2016-11-01',
                             'date_end': '2016-1-01',
                             })
        with self.assertRaises(except_orm):
            track.button_ok()
        # 按产品搜索
        self.track.goods_id = 1
        self.track.button_ok()
        # 按客户搜索
        self.track.goods_id = False
        self.track.partner_id = self.env.ref('core.yixun').id
        self.track.button_ok()
        # 按销售员搜索
        self.track.goods_id = False
        self.track.partner_id = False
        self.track.staff_id = self.env.ref('core.lili').id
        self.track.button_ok()
        # 按日期搜索
        self.track.goods_id = False
        self.track.partner_id = False
        self.track.staff_id = False
        self.track.button_ok()


class test_detail_wizard(TransactionCase):
    '''测试销售订单明细表向导'''

    def setUp(self):
        ''' 准备报表数据 '''
        super(test_detail_wizard, self).setUp()
        # 补足产品网线的数量
        warehouse_obj = self.env.ref('warehouse.wh_in_whin0')
        warehouse_obj.approve_order()
        # 复制一张销货订单并审核
        self.order = self.env.ref('sell.sell_order_2')
        order_2 = self.order.copy()
        order_2.sell_order_done()

        # 审核出库单
        delivery_2 = self.env['sell.delivery'].search(
                    [('order_id', '=', order_2.id)])
        delivery_2.sell_delivery_done()

        # 销货订单产生退货单，并审核退货单
        sell_return = self.env.ref('sell.sell_order_return')
        sell_return.sell_order_done()
        delivery_return = self.env['sell.delivery'].search(
                    [('order_id', '=', sell_return.id)])
        delivery_return.sell_delivery_done()

        self.detail_obj = self.env['sell.order.detail.wizard']
        self.detail = self.detail_obj.create({})

    def test_button_ok(self):
        '''测试销售订单明细表确认按钮'''
        detail = self.detail_obj.create({
                             'date_start': '2016-11-01',
                             'date_end': '2016-1-01',
                             })
        with self.assertRaises(except_orm):
            detail.button_ok()
        # 按产品搜索
        self.detail.goods_id = 1
        self.detail.button_ok()
        # 按客户搜索
        self.detail.goods_id = False
        self.detail.partner_id = self.env.ref('core.yixun').id
        self.detail.button_ok()
        # 按销售员搜索
        self.detail.goods_id = False
        self.detail.partner_id = False
        self.detail.staff_id = self.env.ref('core.lili').id
        self.detail.button_ok()
        # 按日期搜索
        self.detail.goods_id = False
        self.detail.partner_id = False
        self.detail.staff_id = False
        self.detail.button_ok()


class test_goods_wizard(TransactionCase):
    '''测试销售汇总表（按商品）向导'''

    def setUp(self):
        ''' 准备报表数据 '''
        super(test_goods_wizard, self).setUp()
        warehouse_obj = self.env.ref('warehouse.wh_in_whin0')
        warehouse_obj.approve_order()
        self.order = self.env.ref('sell.sell_order_2')
        self.order.sell_order_done()
        self.delivery = self.env['sell.delivery'].search(
                       [('order_id', '=', self.order.id)])
        self.delivery.sell_delivery_done()
        self.goods_obj = self.env['sell.summary.goods.wizard']
        self.goods = self.goods_obj.create({})

    def test_button_ok(self):
        '''销售汇总表（按商品）向导确认按钮'''
        # 日期报错
        goods = self.goods_obj.create({
                             'date_start': '2016-11-01',
                             'date_end': '2016-1-01',
                             })
        with self.assertRaises(except_orm):
            goods.button_ok()

    def test_goods_report(self):
        '''测试销售汇总表（按商品）报表'''
        summary_goods = self.env['sell.summary.goods'].create({})
        context = self.goods.button_ok().get('context')
        results = summary_goods.with_context(context).search_read(domain=[])
        new_goods_wizard = self.goods.copy()
        new_goods_wizard.goods_id = 3
        new_goods_wizard.partner_id = 3
        goods_categ_id = self.env.ref('core.goods_category_1')
        new_goods_wizard.goods_categ_id = goods_categ_id.id
        new_context = new_goods_wizard.button_ok().get('context')
        new_results = summary_goods.with_context(new_context).search_read(
                                                                  domain=[])
        self.assertEqual(len(results), 1)
        self.assertEqual(len(new_results), 0)
