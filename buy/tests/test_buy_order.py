# -*- coding: utf-8 -*-
from odoo.tests.common import TransactionCase
from odoo.exceptions import UserError


class test_buy_order(TransactionCase):

    def setUp(self):
        super(test_buy_order, self).setUp()
        # 给buy_order_1中的产品“键盘”的分类设置科目
        self.env.ref('core.goods_category_1').account_id = self.env.ref('finance.account_goods').id
        self.order = self.env.ref('buy.buy_order_1')
        self.order.bank_account_id = False

        # 因同一个业务伙伴不能存在两张未审核的收付款单，把系统里已有的相关业务伙伴未审核的收付款单审核
        self.env.ref('money.get_40000').money_order_done()
        self.env.ref('money.pay_2000').money_order_done()

    def test_onchange_discount_rate(self):
        ''' 优惠率改变时，改变优惠金额，优惠后金额也改变'''
        amount_before = self.order.amount
        discount_amount_before = self.order.discount_amount
        self.order.discount_rate = 10
        self.order.onchange_discount_rate()
        self.assertTrue(self.order.amount != amount_before)
        self.assertTrue(self.order.discount_amount != discount_amount_before)

    def test_get_buy_goods_state(self):
        '''返回收货状态'''
        # order产品总数量为10
        self.order.buy_order_done()
        # 采购订单行的已入库数量为0时，将产品状态写为未入库
        self.order._get_buy_goods_state()
        self.assertTrue(self.order.goods_state == u'未入库')
        receipt = self.env['buy.receipt'].search(
                  [('order_id', '=', self.order.id)])
        # 采购订单行的已入库数量等于产品数量时，将产品状态写为全部入库
        receipt.buy_receipt_done()
        self.order._get_buy_goods_state()
        self.assertTrue(self.order.goods_state == u'全部入库')
        # 采购订单行的已入库数量小于产品数量时，将产品状态写为部分入库
        order_copy_1 = self.order.copy()
        order_copy_1.buy_order_done()
        receipt = self.env['buy.receipt'].search(
                  [('order_id', '=', order_copy_1.id)])
        for line in receipt.line_in_ids:
            line.goods_qty = 5
        receipt.buy_receipt_done()
        order_copy_1._get_buy_goods_state()
        self.assertTrue(order_copy_1.goods_state == u'部分入库')

    def test_default_warehouse_dest(self):
        '''新建购货订单时默认调入仓库'''
        order = self.env['buy.order'].with_context({
             'warehouse_dest_type': 'stock'
             }).create({})
        self.assertTrue(order.warehouse_dest_id.type == 'stock')
        self.env['buy.order'].create({})

    def test_get_money_state(self):
        '''计算购货订单付款/退款状态'''
        self.order.buy_order_done()
        receipt = self.env['buy.receipt'].search(
                  [('order_id', '=', self.order.id)])
        # 入库单不付款，购货订单付款状态应该为未付款
        receipt.buy_receipt_done()
        self.order._get_money_state()
        self.assertTrue(self.order.money_state == u'未付款')

        # 入库单总金额为585，本次付500，购货订单付款状态应该为部分付款
        receipt.buy_receipt_draft()
        bank_account = self.env.ref('core.alipay')
        bank_account.balance = 1000000
        receipt.payment = 500
        receipt.bank_account_id = bank_account
        receipt.buy_receipt_done()
        # 查找产生的付款单，并审核
        source_line = self.env['source.order.line'].search(
                [('name', '=', receipt.invoice_id.id)])
        for line in source_line:
            line.money_id.money_order_done()
        # 判断状态
        self.order._get_money_state()
        self.assertTrue(self.order.money_state == u'部分付款')

        # 入库单总金额为585，本次付585，购货订单付款状态应该为全部付款
        receipt.buy_receipt_draft()
        bank_account = self.env.ref('core.alipay')
        bank_account.balance = 1000000
        receipt.payment = 585
        receipt.bank_account_id = bank_account
        receipt.buy_receipt_done()
        # 查找产生的付款单，并审核
        source_line = self.env['source.order.line'].search(
                [('name', '=', receipt.invoice_id.id)])
        for line in source_line:
            line.money_id.money_order_done()
        # 判断状态
        self.order._get_money_state()
        self.assertTrue(self.order.money_state == u'全部付款')

    def test_unlink(self):
        '''测试删除已审核的采购订单'''
        self.order.buy_order_done()
        with self.assertRaises(UserError):
            self.order.unlink()
        # 删除草稿状态的采购订单
        self.order.copy()
        self.order.buy_order_draft()
        self.order.unlink()

    def test_buy_order_done(self):
        '''采购订单审核'''
        # 正常审核
        self.order.buy_order_done()
        self.assertTrue(self.order.state == 'done')
        # 重复审核报错
        with self.assertRaises(UserError):
            self.order.buy_order_done()
        # 数量单价小于0应报错
        self.order.buy_order_draft()
        for line in self.order.line_ids:
            line.quantity = 0
        with self.assertRaises(UserError):
            self.order.buy_order_done()

        # 输入预付款和结算账户
        bank_account = self.env.ref('core.alipay')
        bank_account.balance = 1000000
        self.order.prepayment = 50.0
        self.order.bank_account_id = bank_account
        for line in self.order.line_ids:
            line.quantity = 1
        self.order.buy_order_done()

        # 预付款不为空时，请选择结算账户
        self.order.buy_order_draft()
        self.order.bank_account_id = False
        self.order.prepayment = 50.0
        with self.assertRaises(UserError):
            self.order.buy_order_done()

        # 没有订单行时审核报错
        for line in self.order.line_ids:
            line.unlink()
        with self.assertRaises(UserError):
            self.order.buy_order_done()

    def test_buy_order_draft(self):
        '''采购订单反审核'''
        # 正常反审核
        self.order.buy_order_done()
        self.order.buy_order_draft()
        receipt = self.env['buy.receipt'].search(
                  [('order_id', '=', self.order.id)])
        self.assertTrue(not receipt)
        self.assertTrue(self.order.state == 'draft')
        self.assertTrue(not self.order.approve_uid.id)
        # 重复反审核报错
        self.order.buy_order_done()
        self.order.buy_order_draft()
        with self.assertRaises(UserError):
            self.order.buy_order_draft()
        # 订单已收货不能反审核
        self.order.buy_order_done()
        receipt = self.env['buy.receipt'].search(
                  [('order_id', '=', self.order.id)])
        receipt.buy_receipt_done()
        with self.assertRaises(UserError):
            self.order.buy_order_draft()

    def test_buy_generate_receipt(self):
        '''测试采购订单生成入库单,批次管理拆分折扣金额'''
        # 采购订单
        # 全部入库
        self.order.buy_order_done()
        receipt = self.env['buy.receipt'].search(
                  [('order_id', '=', self.order.id)])
        receipt.buy_receipt_done()
        self.order.buy_generate_receipt()
        self.assertTrue(self.order.goods_state == u'全部入库')
        # 批次管理拆分订单行
        new_order = self.order.copy()
        for line in new_order.line_ids:
            line.goods_id = self.env.ref('goods.mouse').id
            new_order.buy_generate_receipt()
        receipt = self.env['buy.receipt'].search(
                  [('order_id', '=', new_order.id)])
        self.assertTrue(len(receipt.line_in_ids) == 10)
        # 退货订单
        # 全部入库
        return_receipt = self.env.ref('buy.buy_return_order_1')
        return_receipt.buy_order_done()
        receipt = self.env['buy.receipt'].search(
                  [('order_id', '=', return_receipt.id)])
        receipt.buy_receipt_done()
        return_receipt.buy_generate_receipt()


class test_buy_order_line(TransactionCase):

    def setUp(self):
        super(test_buy_order_line, self).setUp()
        self.order = self.env.ref('buy.buy_order_1')
        self.cable = self.env.ref('goods.cable')

    def test_compute_using_attribute(self):
        '''返回订单行中产品是否使用属性'''
        for line in self.order.line_ids:
            self.assertTrue(line.using_attribute)
            line.goods_id = self.env.ref('goods.mouse')
            self.assertTrue(not line.using_attribute)

    def test_compute_all_amount(self):
        '''当订单行的数量、含税单价、折扣额、税率改变时，改变购货金额、税额、价税合计'''
        for line in self.order.line_ids:
            line.price_taxed = 11.7
            self.assertTrue(line.amount == 100)
            self.assertTrue(line.tax_amount == 17)
            self.assertAlmostEqual(line.price_taxed, 11.7)
            self.assertTrue(line.subtotal == 117)

    def test_compute_all_amount_wrong_tax_rate(self):
        '''明细行上输入错误税率，应报错'''
        for line in self.order.line_ids:
            with self.assertRaises(UserError):
                line.tax_rate = -1
            with self.assertRaises(UserError):
                line.tax_rate = 102

    def test_onchange_goods_id(self):
        '''当订单行的产品变化时，带出产品上的单位、成本'''
        for line in self.order.line_ids:
            line.goods_id = self.cable
            line.onchange_goods_id()
            self.assertTrue(line.uom_id.name == u'件')

            # 测试价格是否是商品的成本
            self.assertTrue(line.price_taxed == self.cable.cost)
            # 测试不设置商品的成本时是否弹出警告
            self.cable.cost = 0.0
            with self.assertRaises(UserError):
                line.onchange_goods_id()

    def test_onchange_goods_id_vendor(self):
        '''当订单行的产品变化时，带出产品上供应商价'''
        # 添加网线的供应商价
        self.cable.vendor_ids.create({
                'goods_id': self.cable.id,
                'vendor_id': self.env.ref('core.lenovo').id,
                'price': 2,})
        # 不选择供应商时，应弹出警告
        self.order.partner_id = False
        for line in self.order.line_ids:
            with self.assertRaises(UserError):
                line.onchange_goods_id()
        # 选择供应商联想，得到供应商价
        self.order.partner_id = self.env.ref('core.lenovo')
        for line in self.order.line_ids:
            line.goods_id = self.cable
            line.onchange_goods_id()
            self.assertTrue(line.price_taxed == 2)

    def test_onchange_discount_rate(self):
        ''' 订单行优惠率改变时，改变优惠金额'''
        for line in self.order.line_ids:
            line.price_taxed = 11.7
            line.discount_rate = 10
            line.onchange_discount_rate()
            self.assertTrue(line.discount_amount == 10)
