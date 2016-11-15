# -*- coding: utf-8 -*-
from odoo.tests.common import TransactionCase
from odoo.exceptions import UserError
from datetime import datetime


class test_sell_order(TransactionCase):

    def setUp(self):
        super(test_sell_order, self).setUp()
        self.env.ref('core.jd').credit_limit = 100000
        self.order = self.env.ref('sell.sell_order_1')

        # 因同一个业务伙伴不能存在两张未审核的收付款单，把系统里已有的相关业务伙伴未审核的收付款单审核
        self.env.ref('money.get_40000').money_order_done()
        self.env.ref('money.pay_2000').money_order_done()

    def test_compute_amount(self):
        ''' 计算字段的测试'''
        self.assertEqual(self.order.amount, 154048.00)

    def test_get_sell_goods_state(self):
        '''返回发货状态'''
        for goods_state in [(u'未出库', 0), (u'部分出库', 1), (u'全部出库', 10000)]:
            self.order.line_ids.write({'quantity_out': goods_state[1]})
            self.assertEqual(self.order.goods_state, goods_state[0])
            if goods_state[1] != 0:
                with self.assertRaises(UserError):
                    self.order.sell_order_done()
                    self.order.sell_order_draft()
            else:
                self.order.sell_order_done()
                self.order.sell_order_draft()

    def test_default_warehouse(self):
        '''新建销货订单时调出仓库的默认值'''
        order = self.env['sell.order'].with_context({
             'warehouse_type': 'stock'
             }).create({})
        self.assertTrue(order.warehouse_id.type == 'stock')
        # 不传 warehouse_type 时
        order2 = self.env['sell.order'].create({})
        self.assertTrue(not order2.warehouse_id)

    def test_get_money_state(self):
        '''计算销货订单收款/退款状态'''
        order2 = self.env.ref('sell.sell_order_2')
        order2.sell_order_done()
        delivery = self.env['sell.delivery'].search(
                  [('order_id', '=', order2.id)])
        # 发货单产品在仓库中不足，需盘点入库以保证审核通过
        self.env.ref('core.goods_category_1').account_id = self.env.ref('finance.account_goods').id
        warehouse_obj = self.env.ref('warehouse.wh_in_whin0')
        warehouse_obj.approve_order()
        # 发货单不付款，销货订单收款状态应该为未收款
        delivery.sell_delivery_done()
        order2._get_money_state()
        self.assertTrue(order2.money_state == u'未收款')
        # 发货单总金额为 73.3，本次收款 50，销货订单收款状态应该为部分收款
        delivery.sell_delivery_draft()
        bank_account = self.env.ref('core.alipay')
        bank_account.balance = 1000000
        delivery.receipt = 50
        delivery.bank_account_id = bank_account.id
        delivery.sell_delivery_done()

        order2._get_money_state()
        self.assertTrue(order2.money_state == u'部分收款')
        # 发货单总金额为 73.3，本次收款 73.3，销货订单收款状态应该为全部收款
        delivery.sell_delivery_draft()
        bank_account = self.env.ref('core.alipay')
        bank_account.balance = 1000000
        delivery.receipt = 75
        delivery.bank_account_id = bank_account.id
        delivery.sell_delivery_done()
        order2._get_money_state()
        self.assertTrue(order2.money_state == u'全部收款')

    def test_onchange_partner_id(self):
        '''选择客户带出其默认地址信息'''
        self.order.onchange_partner_id()

    def test_onchange_discount_rate(self):
        ''' sell.order onchange test '''
        self.order.discount_rate = 10
        self.order.onchange_discount_rate()
        self.assertEqual(self.order.discount_amount, 15408.0)

    def test_unlink(self):
        '''测试删除已审核的销货订单'''
        self.order.sell_order_done()
        with self.assertRaises(UserError):
            self.order.unlink()
        # 删除草稿状态的销货订单
        self.order.copy()
        self.order.sell_order_draft()
        self.order.unlink()

    def test_sell_order_done(self):
        '''测试审核销货订单'''
        # 审核销货订单
        self.order.sell_order_done()
        with self.assertRaises(UserError):
            self.order.sell_order_done()

        # 未填数量应报错
        self.order.sell_order_draft()
        for line in self.order.line_ids:
            line.quantity = 0
        with self.assertRaises(UserError):
            self.order.sell_order_done()

        # 输入预收款和结算账户
        bank_account = self.env.ref('core.alipay')
        bank_account.balance = 1000000
        self.order.pre_receipt = 50.0
        self.order.bank_account_id = bank_account
        for line in self.order.line_ids:
            line.quantity = 1
        self.order.sell_order_done()

        # 预收款不为空时，请选择结算账户！
        self.order.sell_order_draft()
        self.order.bank_account_id = False
        self.order.pre_receipt = 50.0
        with self.assertRaises(UserError):
            self.order.sell_order_done()

    def test_sell_order_done_no_line(self):
        '''没有订单行时审核报错'''
        for line in self.order.line_ids:
            line.unlink()
        with self.assertRaises(UserError):
            self.order.sell_order_done()

    def test_sell_order_done_foreign_currency(self):
        '''测试审核销货订单，外币免税'''
        self.order.currency_id = self.env.ref('base.USD')
        for line in self.order.line_ids:
            line.price_taxed = 1170
            line.tax_rate = 17
        with self.assertRaises(UserError):
            self.order.sell_order_done()

    def test_sell_order_draft(self):
        ''' 测试反审核销货订单  '''
        self.order.sell_order_done()
        self.order.sell_order_draft()
        with self.assertRaises(UserError):
            self.order.sell_order_draft()


class test_sell_order_line(TransactionCase):

    def setUp(self):
        super(test_sell_order_line, self).setUp()
        self.order = self.env.ref('sell.sell_order_1')
        self.sell_order_line = self.env.ref('sell.sell_order_line_2_3')

    def test_compute_using_attribute(self):
        '''返回订单行中产品是否使用属性'''
        for line in self.order.line_ids:
            self.assertTrue(not line.using_attribute)
            line.goods_id = self.env.ref('goods.keyboard')
            self.assertTrue(line.using_attribute)

    def test_compute_all_amount(self):
        ''' 销售订单行计算字段的测试 '''
        self.assertEqual(self.sell_order_line.amount, 91.45)  # tax_amount subtotal
        self.assertEqual(self.sell_order_line.tax_rate, 17.0)
        self.assertEqual(self.sell_order_line.tax_amount, 15.55)
        self.assertEqual(self.sell_order_line.subtotal, 107)

    def test_compute_all_amount_foreign_currency(self):
        '''外币测试：当订单行的数量、含税单价、折扣额、税率改变时，改变销售金额、税额、价税合计'''
        self.order.currency_id = self.env.ref('base.EUR')
        for line in self.order.line_ids:
            line.price_taxed = 11.7

    def test_compute_all_amount_wrong_tax_rate(self):
        '''明细行上输入错误税率，应报错'''
        for line in self.order.line_ids:
            with self.assertRaises(UserError):
                line.tax_rate = -1
            with self.assertRaises(UserError):
                line.tax_rate = 102

    def test_onchange_goods_id(self):
        '''当销货订单行的产品变化时，带出产品上的单位、价格'''
        goods = self.env.ref('goods.keyboard')
        c_category_id = self.order.partner_id.c_category_id

        for line in self.order.line_ids:
            line.goods_id = goods
            line.onchange_goods_id()
            self.assertTrue(line.uom_id.name == u'件')
            # 测试价格是否是商品的销售价
            self.assertTrue(line.price_taxed == goods.price)
                
    def test_onchange_warehouse_id(self):
        '''仓库和商品带出价格策略的折扣率'''
        order_line=self.env.ref('sell.sell_order_line_1')
        order_line.onchange_warehouse_id()
        order=self.env.ref('sell.sell_order_1')
        order.partner_id = self.env.ref('core.yixun').id
        order_line.onchange_warehouse_id()

        # 找不到价格策略时
        order.date = False
        order_line.onchange_warehouse_id()

    def test_onchange_discount_rate(self):
        ''' 销售订单行 折扣率 on_change'''
        self.sell_order_line.discount_rate = 20
        self.sell_order_line.onchange_discount_rate()
        self.assertEqual(self.sell_order_line.amount, 82.91)
