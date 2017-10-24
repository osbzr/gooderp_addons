# -*- coding: utf-8 -*-
from odoo.tests.common import TransactionCase
from odoo.exceptions import UserError


class TestSellAdjust(TransactionCase):

    def setUp(self):
        '''销售变更单准备基本数据'''
        super(TestSellAdjust, self).setUp()
        self.env.ref('core.jd').credit_limit = 100000
        self.env.ref('core.goods_category_1').account_id = self.env.ref(
            'finance.account_goods').id
        self.env.ref('warehouse.wh_in_whin0').date = '2016-02-06'

        # 销货订单 10个 网线
        self.order = self.env.ref('sell.sell_order_2')
        self.order.sell_order_done()
        self.keyboard = self.env.ref('goods.keyboard')
        self.keyboard_white = self.env.ref('goods.keyboard_white')
        self.mouse = self.env.ref('goods.mouse')
        self.cable = self.env.ref('goods.cable')
        # 因为下面要用到 商品在系统里面必须是有数量的 所以,找到一个简单的方式直接确认已有的盘点单
        warehouse_obj = self.env.ref('warehouse.wh_in_whin0')
        warehouse_obj.approve_order()

    def test_unlink(self):
        '''测试删除已审核的销售变更单'''
        adjust = self.env['sell.adjust'].create({
            'order_id': self.order.id,
            'line_ids': [(0, 0, {'goods_id': self.cable.id,
                                 'quantity': 2,
                                 }),
                         ]
        })
        adjust.sell_adjust_done()
        with self.assertRaises(UserError):
            adjust.unlink()
        # 删除草稿状态的销售变更单
        new = adjust.copy()
        new.unlink()

    def test_sell_adjust_done(self):
        '''审核销售变更单:正常情况'''
        # 正常情况下审核，新增商品鼠标（每批次为1的）、键盘（无批次的）
        adjust = self.env['sell.adjust'].create({
            'order_id': self.order.id,
            'line_ids': [(0, 0, {'goods_id': self.cable.id,
                                 'quantity': 2,
                                 }),
                         (0, 0, {'goods_id': self.mouse.id,
                                 'quantity': 1,
                                 }),
                         (0, 0, {'goods_id': self.keyboard.id,
                                 'attribute_id': self.keyboard_white.id,
                                 'quantity': 1,
                                 })
                         ]
        })
        adjust.sell_adjust_done()
        # 重复审核时报错
        with self.assertRaises(UserError):
            adjust.sell_adjust_done()

    def test_sell_adjust_done_no_line(self):
        '''审核销售变更单:没输入明细行，审核时报错'''
        adjust = self.env['sell.adjust'].create({
            'order_id': self.order.id,
        })
        with self.assertRaises(UserError):
            adjust.sell_adjust_done()

    def test_sell_adjust_done_all_in(self):
        '''审核销售变更单：销货订单生成的发货单已全部出库，审核时报错'''
        new_order = self.order.copy()
        new_order.sell_order_done()
        delivery = self.env['sell.delivery'].search(
            [('order_id', '=', new_order.id)])
        delivery.discount_amount = 0    # 订单行中价格为0，所以整单金额0
        delivery.sell_delivery_done()
        adjust = self.env['sell.adjust'].create({
            'order_id': new_order.id,
            'line_ids': [(0, 0, {'goods_id': self.cable.id,
                                 'quantity': 1,
                                 }),
                         ]
        })
        with self.assertRaises(UserError):
            adjust.sell_adjust_done()

    def test_sell_adjust_done_more_same_line(self):
        '''审核销售变更单：查找到销货订单中多行同一商品，不能调整'''
        new_order = self.order.copy()
        new_order.line_ids.create({'order_id': new_order.id,
                                   'goods_id': self.cable.id,
                                   'quantity': 10,
                                   'price_taxed': 10.0,
                                   })
        new_order.sell_order_done()
        delivery = self.env['sell.delivery'].search(
            [('order_id', '=', new_order.id)])
        for line in delivery.line_out_ids:
            line.goods_qty = 1
        delivery.discount_amount = 0    # 订单行中价格为0，所以整单金额0
        delivery.sell_delivery_done()
        adjust = self.env['sell.adjust'].create({
            'order_id': new_order.id,
            'line_ids': [(0, 0, {'goods_id': self.cable.id,
                                 'quantity': 3.0,
                                 }),
                         ]
        })
        with self.assertRaises(UserError):
            adjust.sell_adjust_done()

    def test_sell_adjust_done_quantity_lt(self):
        '''审核销售变更单：调整后数量 5 < 原订单已出库数量 6，审核时报错'''
        delivery = self.env['sell.delivery'].search(
            [('order_id', '=', self.order.id)])
        for line in delivery.line_out_ids:
            line.goods_qty = 6
        delivery.sell_delivery_done()
        adjust = self.env['sell.adjust'].create({
            'order_id': self.order.id,
            'line_ids': [(0, 0, {'goods_id': self.cable.id,
                                 'quantity': -5,
                                 })]
        })
        with self.assertRaises(UserError):
            adjust.sell_adjust_done()

    def test_sell_adjust_done_quantity_equal(self):
        '''审核销售变更单:调整后数量6 == 原订单已出库数量 6，审核后将产生的发货单分单删除'''
        delivery = self.env['sell.delivery'].search(
            [('order_id', '=', self.order.id)])
        for line in delivery.line_out_ids:
            line.goods_qty = 6
        delivery.sell_delivery_done()
        adjust = self.env['sell.adjust'].create({
            'order_id': self.order.id,
            'line_ids': [(0, 0, {'goods_id': self.cable.id,
                                 'quantity': -4,
                                 })]
        })
        adjust.sell_adjust_done()
        new_delivery = self.env['sell.delivery'].search(
            [('order_id', '=', self.order.id),
             ('state', '=', 'draft')])
        self.assertTrue(not new_delivery)

    def test_sell_adjust_done_goods_done(self):
        '''审核销售变更单:原始单据中一行商品已全部出库，另一行没有'''
        new_order = self.order.copy()
        new_order.line_ids.create({'order_id': new_order.id,
                                   'goods_id': self.keyboard.id,
                                   'attribute_id': self.keyboard_white.id,
                                   'quantity': 10,
                                   'price_taxed': 10.0,
                                   })
        new_order.sell_order_done()
        delivery = self.env['sell.delivery'].search(
            [('order_id', '=', new_order.id)])
        for line in delivery.line_out_ids:
            if line.goods_id.id != self.keyboard.id:
                line.unlink()
        delivery.discount_amount = 0    # 订单行中价格为0，所以整单金额0
        delivery.sell_delivery_done()
        adjust = self.env['sell.adjust'].create({
            'order_id': new_order.id,
            'line_ids': [(0, 0, {'goods_id': self.keyboard.id,
                                 'attribute_id': self.keyboard_white.id,
                                 'quantity': 3.0,
                                 }),
                         ]
        })
        with self.assertRaises(UserError):
            adjust.sell_adjust_done()


class TestSellAdjustLine(TransactionCase):

    def setUp(self):
        '''销售变更单明细基本数据'''
        super(TestSellAdjustLine, self).setUp()
        # 销货订单 10个 网线
        self.order = self.env.ref('sell.sell_order_2')
        self.order.sell_order_done()
        self.keyboard = self.env.ref('goods.keyboard')
        self.cable = self.env.ref('goods.cable')
        self.adjust = self.env['sell.adjust'].create({
            'order_id': self.order.id,
            'line_ids': [(0, 0, {'goods_id': self.cable.id,
                                 'quantity': 1,
                                 })]
        })

    def test_compute_using_attribute(self):
        '''返回订单行中商品是否使用属性'''
        for line in self.adjust.line_ids:
            self.assertTrue(not line.using_attribute)
            line.goods_id = self.keyboard
            self.assertTrue(line.using_attribute)

    def test_compute_all_amount(self):
        '''当订单行的数量、单价、折扣额、税率改变时，改变销货金额、税额、价税合计'''
        for line in self.adjust.line_ids:
            line.price_taxed = 117
            self.assertTrue(line.amount == 100)
            self.assertTrue(line.tax_amount == 17)
            self.assertTrue(line.price_taxed == 117)
            self.assertTrue(line.subtotal == 117)

    def test_inverse_price(self):
        '''由不含税价反算含税价，保存时生效'''
        for line in self.adjust.line_ids:
            line.price = 10
            self.assertAlmostEqual(line.price_taxed, 11.7)

    def test_onchange_price(self):
        '''当订单行的不含税单价改变时，改变含税单价'''
        for line in self.adjust.line_ids:
            line.price_taxed = 0
            line.price = 10
            line.onchange_price()
            self.assertAlmostEqual(line.price_taxed, 11.7)

    def test_compute_all_amount_wrong_tax_rate(self):
        '''明细行上输入错误税率，应报错'''
        for line in self.adjust.line_ids:
            with self.assertRaises(UserError):
                line.tax_rate = -1
            with self.assertRaises(UserError):
                line.tax_rate = 102

    def test_onchange_goods_id(self):
        '''当销货订单行的商品变化时，带出商品上的单位、价格'''
        for line in self.adjust.line_ids:
            line.goods_id = self.keyboard
            line.onchange_goods_id()
            self.assertTrue(line.uom_id.name == u'件')

    def test_onchange_discount_rate(self):
        ''' 订单行优惠率改变时，改变优惠金额'''
        for line in self.adjust.line_ids:
            line.price_taxed = 117
            line.discount_rate = 10
            line.onchange_discount_rate()

    def test_onchange_goods_id_tax_rate(self):
        ''' 测试 修改商品时，调整单行税率变化 '''
        self.adjust.partner_id = self.env.ref('core.jd')
        for order_line in self.adjust.line_ids:
            # partner 无 税率，调整单行商品无税率
            self.env.ref('core.jd').tax_rate = 0
            self.env.ref('goods.cable').tax_rate = 0
            order_line.onchange_goods_id()
            # partner 有 税率，调整单行商品无税率
            self.env.ref('core.jd').tax_rate = 10
            self.env.ref('goods.cable').tax_rate = 0
            order_line.onchange_goods_id()
            # partner 无税率，调整单行商品有税率
            self.env.ref('core.jd').tax_rate = 0
            self.env.ref('goods.cable').tax_rate = 10
            order_line.onchange_goods_id()
            # partner 税率 > 调整单行商品税率
            self.env.ref('core.jd').tax_rate = 11
            self.env.ref('goods.cable').tax_rate = 10
            order_line.onchange_goods_id()
            # partner 税率 =< 调整单行商品税率
            self.env.ref('core.jd').tax_rate = 9
            self.env.ref('goods.cable').tax_rate = 10
            order_line.onchange_goods_id()
