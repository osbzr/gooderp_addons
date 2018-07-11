# -*- coding: utf-8 -*-
from odoo.tests.common import TransactionCase
from odoo.exceptions import UserError


class TestBuyAdjust(TransactionCase):

    def setUp(self):
        '''采购变更单准备基本数据'''
        super(TestBuyAdjust, self).setUp()
        self.order = self.env.ref('buy.buy_order_1')
        for line in self.order.line_ids:
            line.tax_rate = 0
        self.order.buy_order_done()
        self.keyboard = self.env.ref('goods.keyboard')
        self.keyboard_black = self.env.ref('goods.keyboard_black')
        self.mouse = self.env.ref('goods.mouse')
        self.cable = self.env.ref('goods.cable')

    def test_unlink(self):
        '''测试删除已审核的采购变更单'''
        adjust = self.env['buy.adjust'].create({
            'order_id': self.order.id,
            'line_ids': [(0, 0, {'goods_id': self.keyboard.id,
                                 'attribute_id': self.keyboard_black.id,
                                 'quantity': 3.0,
                                 }),
                         ]
        })
        adjust.buy_adjust_done()
        with self.assertRaises(UserError):
            adjust.unlink()
        # 删除草稿状态的采购变更单
        new = adjust.copy()
        new.unlink()

    def test_buy_adjust_done(self):
        '''审核采购变更单:正常情况'''
        # 正常情况下审核，新增商品鼠标（每批次为1的）、网线（无批次的）
        adjust = self.env['buy.adjust'].create({
            'order_id': self.order.id,
            'line_ids': [(0, 0, {'goods_id': self.keyboard.id,
                                 'attribute_id': self.keyboard_black.id,
                                 'quantity': 3.0,
                                 }),
                         (0, 0, {'goods_id': self.mouse.id,
                                 'quantity': 1,
                                 'lot': 'mouse001',
                                 }),
                         (0, 0, {'goods_id': self.cable.id,
                                 'quantity': 1,
                                 })
                         ]
        })
        adjust.buy_adjust_done()
        # 重复审核时报错
        with self.assertRaises(UserError):
            adjust.buy_adjust_done()

    def test_buy_adjust_done_no_line(self):
        '''审核采购变更单:没输入明细行，审核时报错'''
        adjust_no_line = self.env['buy.adjust'].create({
            'order_id': self.order.id,
        })
        with self.assertRaises(UserError):
            adjust_no_line.buy_adjust_done()

    def test_buy_adjust_done_price_negative(self):
        '''审核采购变更单:商品价格为负，审核时报错'''
        adjust = self.env['buy.adjust'].create({
            'order_id': self.order.id,
            'line_ids': [(0, 0, {'goods_id': self.keyboard.id,
                                 'attribute_id': self.keyboard_black.id,
                                 'quantity': 3,
                                 'price_taxed': -1,
                                 })]
        })
        with self.assertRaises(UserError):
            adjust.buy_adjust_done()

    def test_buy_adjust_done_quantity_lt(self):
        '''审核采购变更单:调整后数量 5 < 原订单已入库数量 6，审核时报错'''
        self.env.ref('core.goods_category_1').account_id = self.env.ref(
            'finance.account_goods').id
        buy_receipt = self.env['buy.receipt'].search(
            [('order_id', '=', self.order.id)])
        for line in buy_receipt.line_in_ids:
            line.goods_qty = 6
        buy_receipt.buy_receipt_done()
        adjust = self.env['buy.adjust'].create({
            'order_id': self.order.id,
            'line_ids': [(0, 0, {'goods_id': self.keyboard.id,
                                 'attribute_id': self.keyboard_black.id,
                                 'quantity': -5,
                                 })]
        })
        with self.assertRaises(UserError):
            adjust.buy_adjust_done()

    def test_buy_adjust_done_quantity_equal(self):
        '''审核采购变更单:调整后数量6 == 原订单已入库数量 6，审核后将产生的入库单分单删除'''
        self.env.ref('core.goods_category_1').account_id = self.env.ref(
            'finance.account_goods').id
        buy_receipt = self.env['buy.receipt'].search(
            [('order_id', '=', self.order.id)])
        for line in buy_receipt.line_in_ids:
            line.goods_qty = 6
        buy_receipt.buy_receipt_done()
        adjust = self.env['buy.adjust'].create({
            'order_id': self.order.id,
            'line_ids': [(0, 0, {'goods_id': self.keyboard.id,
                                 'attribute_id': self.keyboard_black.id,
                                 'quantity': -4,
                                 })]
        })
        adjust.buy_adjust_done()
        new_receipt = self.env['buy.receipt'].search(
            [('order_id', '=', self.order.id),
             ('state', '=', 'draft')])
        self.assertTrue(not new_receipt)

    def test_buy_adjust_done_all_in(self):
        '''审核采购变更单：购货订单生成的采购入库单已全部入库，审核时报错'''
        self.env.ref('core.goods_category_1').account_id = self.env.ref(
            'finance.account_goods').id
        receipt = self.env['buy.receipt'].search(
            [('order_id', '=', self.order.id)])
        receipt.buy_receipt_done()
        adjust = self.env['buy.adjust'].create({
            'order_id': self.order.id,
            'line_ids': [(0, 0, {'goods_id': self.keyboard.id,
                                 'attribute_id': self.keyboard_black.id,
                                 'quantity': 3.0,
                                 }),
                         ]
        })
        with self.assertRaises(UserError):
            adjust.buy_adjust_done()

    def test_buy_adjust_done_more_same_line(self):
        '''审核采购变更单：查找到购货订单中多行同一商品，不能调整'''
        self.env.ref('core.goods_category_1').account_id = self.env.ref(
            'finance.account_goods').id
        self.order.buy_order_draft()
        self.order.line_ids.create({'order_id': self.order.id,
                                    'goods_id': self.keyboard.id,
                                    'attribute_id': self.keyboard_black.id,
                                    'quantity': 10,
                                    'price_taxed': 10.0,
                                    'tax_rate': 0, })
        self.order.buy_order_done()
        receipt = self.env['buy.receipt'].search(
            [('order_id', '=', self.order.id)])
        for line in receipt.line_in_ids:
            line.goods_qty = 1
        receipt.buy_receipt_done()
        adjust = self.env['buy.adjust'].create({
            'order_id': self.order.id,
            'line_ids': [(0, 0, {'goods_id': self.keyboard.id,
                                 'attribute_id': self.keyboard_black.id,
                                 'quantity': 3.0,
                                 }),
                         ]
        })
        with self.assertRaises(UserError):
            adjust.buy_adjust_done()

    def test_buy_adjust_done_goods_done(self):
        '''审核采购变更单:原始单据中一行商品已全部入库，另一行没有'''
        self.env.ref('core.goods_category_1').account_id = self.env.ref(
            'finance.account_goods').id
        self.order.buy_order_draft()
        self.order.line_ids.create({'order_id': self.order.id,
                                    'goods_id': self.cable.id,
                                    'price_taxed': 10.0,
                                    'quantity': 10,
                                    'tax_rate': 0})
        self.order.buy_order_done()
        receipt = self.env['buy.receipt'].search(
            [('order_id', '=', self.order.id)])
        for line in receipt.line_in_ids:
            if line.goods_id.id != self.cable.id:
                line.unlink()
        receipt.buy_receipt_done()
        adjust = self.env['buy.adjust'].create({
            'order_id': self.order.id,
            'line_ids': [(0, 0, {'goods_id': self.cable.id,
                                 'quantity': 3.0,
                                 }),
                         ]
        })
        with self.assertRaises(UserError):
            adjust.buy_adjust_done()

    def test_buy_adjust_done_no_attribute(self):
        '''检查属性是否填充'''
        adjust = self.env['buy.adjust'].create({
            'order_id': self.order.id,
            'line_ids': [(0, 0, {'goods_id': self.env.ref('goods.keyboard').id,
                                 'quantity': 10,
                                 })]
        })
        with self.assertRaises(UserError):
            adjust.buy_adjust_done()


class TestBuyAdjustLine(TransactionCase):

    def setUp(self):
        super(TestBuyAdjustLine, self).setUp()
        # 采购 10个键盘 单价 50
        self.order = self.env.ref('buy.buy_order_1')
        self.order.buy_order_done()
        self.keyboard = self.env.ref('goods.keyboard')
        self.cable = self.env.ref('goods.cable')
        self.adjust = self.env['buy.adjust'].create({
            'order_id': self.order.id,
            'line_ids': [(0, 0, {'goods_id': self.cable.id,
                                 'quantity': 10,
                                 })]
        })

    def test_compute_using_attribute(self):
        '''返回订单行中商品是否使用属性'''
        for line in self.adjust.line_ids:
            self.assertTrue(not line.using_attribute)
            line.goods_id = self.keyboard
            self.assertTrue(line.using_attribute)

    def test_compute_all_amount(self):
        '''当订单行的数量、单价、折扣额、税率改变时，改变购货金额、税额、价税合计'''
        for line in self.adjust.line_ids:
            line.price_taxed = 11.7
            self.assertTrue(line.amount == 100)
            self.assertTrue(line.tax_amount == 17)
            self.assertTrue(line.subtotal == 117)

    def test_compute_all_amount_wrong_tax_rate(self):
        '''明细行上输入错误税率，应报错'''
        for line in self.adjust.line_ids:
            with self.assertRaises(UserError):
                line.tax_rate = -1
            with self.assertRaises(UserError):
                line.tax_rate = 102

    def test_onchange_price(self):
        '''当订单行的不含税单价改变时，改变含税单价'''
        for line in self.adjust.line_ids:
            line.price_taxed = 0
            line.price = 10
            line.onchange_price()
            self.assertAlmostEqual(line.price_taxed, 11.7)

    def test_onchange_goods_id(self):
        '''当订单行的商品变化时，带出商品上的单位、成本'''
        for line in self.adjust.line_ids:
            line.goods_id = self.cable
            line.onchange_goods_id()
            self.assertTrue(line.uom_id.name == u'件')

            # 测试价格是否是商品的成本
            self.assertTrue(line.price_taxed == self.cable.cost)

    def test_onchange_discount_rate(self):
        ''' 订单行优惠率改变时，改变优惠金额'''
        for line in self.adjust.line_ids:
            line.price_taxed = 11.7
            line.discount_rate = 10
            line.onchange_discount_rate()
            self.assertTrue(line.discount_amount == 10)

    def test_onchange_goods_id_tax_rate(self):
        ''' 测试 修改商品时，商品行税率变化 '''
        for order_line in self.adjust.line_ids:
            # partner 无 税率，采购调整单行商品无税率
            self.env.ref('core.lenovo').tax_rate = 0
            self.env.ref('goods.cable').tax_rate = 0
            order_line.onchange_goods_id()
            # partner 有 税率，采购调整单行商品无税率
            self.env.ref('core.lenovo').tax_rate = 10
            self.env.ref('goods.cable').tax_rate = 0
            order_line.onchange_goods_id()
            # partner 无税率，采购调整单行商品有税率
            self.env.ref('core.lenovo').tax_rate = 0
            self.env.ref('goods.cable').tax_rate = 10
            order_line.onchange_goods_id()
            # partner 税率 > 采购调整单行商品税率
            self.env.ref('core.lenovo').tax_rate = 11
            self.env.ref('goods.cable').tax_rate = 10
            order_line.onchange_goods_id()
            # partner 税率 =< 入库单行商品税率
            self.env.ref('core.lenovo').tax_rate = 9
            self.env.ref('goods.cable').tax_rate = 10
            order_line.onchange_goods_id()
