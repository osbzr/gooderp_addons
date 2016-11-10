# -*- coding: utf-8 -*-
from odoo.tests.common import TransactionCase
from odoo.exceptions import UserError


class test_buy_adjust(TransactionCase):

    def setUp(self):
        '''采购调整单准备基本数据'''
        super(test_buy_adjust, self).setUp()
        self.order = self.env.ref('buy.buy_order_1')
        self.order.buy_order_done()
        self.keyboard = self.env.ref('goods.keyboard')
        self.keyboard_black = self.env.ref('goods.keyboard_black')
        self.mouse = self.env.ref('goods.mouse')
        self.cable = self.env.ref('goods.cable')

    def test_unlink(self):
        '''测试删除已审核的采购调整单'''
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
        # 删除草稿状态的采购调整单
        new = adjust.copy()
        new.unlink()

    def test_buy_adjust_done(self):
        '''审核采购调整单:正常情况'''
        # 正常情况下审核，新增产品鼠标（每批次为1的）、网线（无批次的）
        adjust = self.env['buy.adjust'].create({
            'order_id': self.order.id,
            'line_ids': [(0, 0, {'goods_id': self.keyboard.id,
                                'attribute_id': self.keyboard_black.id,
                                'quantity': 3.0,
                                }),
                        (0, 0, {'goods_id': self.mouse.id,
                               'quantity': 1,
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
        '''审核采购调整单:没输入明细行，审核时报错'''
        adjust_no_line = self.env['buy.adjust'].create({
            'order_id': self.order.id,
        })
        with self.assertRaises(UserError):
            adjust_no_line.buy_adjust_done()

    def test_buy_adjust_done_price_negative(self):
        '''审核采购调整单:产品价格为负，审核时报错'''
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
        '''审核采购调整单:调整后数量 5 < 原订单已入库数量 6，审核时报错'''
        self.env.ref('core.goods_category_1').account_id = self.env.ref('finance.account_goods').id
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
        '''审核采购调整单:调整后数量6 == 原订单已入库数量 6，审核后将产生的入库单分单删除'''
        self.env.ref('core.goods_category_1').account_id = self.env.ref('finance.account_goods').id
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
        '''审核采购调整单：购货订单生成的采购入库单已全部入库，审核时报错'''
        self.env.ref('core.goods_category_1').account_id = self.env.ref('finance.account_goods').id
        new_order = self.order.copy()
        new_order.buy_order_done()
        receipt = self.env['buy.receipt'].search(
            [('order_id', '=', new_order.id)])
        receipt.buy_receipt_done()
        adjust = self.env['buy.adjust'].create({
            'order_id': new_order.id,
            'line_ids': [(0, 0, {'goods_id': self.keyboard.id,
                                'attribute_id': self.keyboard_black.id,
                                'quantity': 3.0,
                                }),
                         ]
        })
        with self.assertRaises(UserError):
            adjust.buy_adjust_done()

    def test_buy_adjust_done_more_same_line(self):
        '''审核采购调整单：查找到购货订单中多行同一产品，不能调整'''
        self.env.ref('core.goods_category_1').account_id = self.env.ref('finance.account_goods').id
        new_order = self.order.copy()
        new_order.line_ids.create({'order_id': new_order.id,
                                   'goods_id': self.keyboard.id,
                                   'attribute_id': self.keyboard_black.id,
                                   'quantity': 10,
                                   'price_taxed': 10.0,})
        new_order.buy_order_done()
        receipt = self.env['buy.receipt'].search(
            [('order_id', '=', new_order.id)])
        for line in receipt.line_in_ids:
            line.goods_qty = 1
        receipt.buy_receipt_done()
        adjust = self.env['buy.adjust'].create({
            'order_id': new_order.id,
            'line_ids': [(0, 0, {'goods_id': self.keyboard.id,
                                'attribute_id': self.keyboard_black.id,
                                'quantity': 3.0,
                                }),
                         ]
        })
        with self.assertRaises(UserError):
            adjust.buy_adjust_done()


    def test_buy_adjust_done_goods_done(self):
        '''审核采购调整单:原始单据中一行产品已全部入库，另一行没有'''
        self.env.ref('core.goods_category_1').account_id = self.env.ref('finance.account_goods').id
        new_order = self.order.copy()
        new_order.line_ids.create({'order_id': new_order.id,
                                   'goods_id': self.cable.id,
                                   'price_taxed': 10.0,
                                   'quantity': 10})
        new_order.buy_order_done()
        receipt = self.env['buy.receipt'].search(
            [('order_id', '=', new_order.id)])
        for line in receipt.line_in_ids:
            if line.goods_id.id != self.cable.id:
                line.unlink()
        receipt.buy_receipt_done()
        adjust = self.env['buy.adjust'].create({
        'order_id': new_order.id,
        'line_ids': [(0, 0, {'goods_id': self.cable.id,
                             'quantity': 3.0,
                            }),
                     ]
        })
        with self.assertRaises(UserError):
            adjust.buy_adjust_done()


class test_buy_adjust_line(TransactionCase):

    def setUp(self):
        super(test_buy_adjust_line, self).setUp()
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
        '''返回订单行中产品是否使用属性'''
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

    def test_onchange_goods_id(self):
        '''当订单行的产品变化时，带出产品上的单位、成本'''
        for line in self.adjust.line_ids:
            line.goods_id = self.cable
            line.onchange_goods_id()
            self.assertTrue(line.uom_id.name == u'件')

            # 测试价格是否是商品的成本
            self.assertTrue(line.price_taxed == self.cable.cost)
            # 测试不设置商品的成本时是否弹出警告
            self.cable.cost = 0.0
            with self.assertRaises(UserError):
                line.onchange_goods_id()

    def test_onchange_discount_rate(self):
        ''' 订单行优惠率改变时，改变优惠金额'''
        for line in self.adjust.line_ids:
            line.price_taxed = 11.7
            line.discount_rate = 10
            line.onchange_discount_rate()
            self.assertTrue(line.discount_amount == 10)
