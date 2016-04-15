# -*- coding: utf-8 -*-
from openerp.tests.common import TransactionCase
from openerp.exceptions import except_orm


class test_buy_order(TransactionCase):

    def setUp(self):
        super(test_buy_order, self).setUp()
        self.order = self.env.ref('buy.buy_order_1')

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

    def test_unlink(self):
        '''测试删除已审核的采购订单'''
        self.order.buy_order_done()
        with self.assertRaises(except_orm):
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
        with self.assertRaises(except_orm):
            self.order.buy_order_done()
        # 没有订单行时审核报错
        self.order.buy_order_draft()
        for line in self.order.line_ids:
            line.unlink()
        with self.assertRaises(except_orm):
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
        self.assertTrue(not self.order.approve_uid)
        # 重复反审核报错
        self.order.buy_order_done()
        self.order.buy_order_draft()
        with self.assertRaises(except_orm):
            self.order.buy_order_draft()
        # 订单已收货不能反审核
        self.order.buy_order_done()
        receipt = self.env['buy.receipt'].search(
                  [('order_id', '=', self.order.id)])
        receipt.buy_receipt_done()
        with self.assertRaises(except_orm):
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
            line.goods_id = 1
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

    def test_default_warehouse(self):
        '''新建订单行调出仓库默认值'''
        self.order.line_ids.with_context({
             'warehouse_type': 'supplier'
             }).create({
                       'order_id': self.order.id,
                       })
        self.order.line_ids.create({
                       'order_id': self.order.id,
                       })

    def test_compute_all_amount(self):
        '''当订单行的数量、单价、折扣额、税率改变时，改变购货金额、税额、价税合计'''
        for line in self.order.line_ids:
            line.price = 10
            self.assertTrue(line.amount == 100)
            self.assertTrue(line.tax_amount == 17)
            self.assertTrue(line.price_taxed == 11.7)
            self.assertTrue(line.subtotal == 117)

    def test_onchange_goods_id(self):
        '''当订单行的产品变化时，带出产品上的单位、默认仓库、成本'''
        goods = self.env.ref('goods.cable')
        goods.default_wh = self.env.ref('warehouse.hd_stock').id
        for line in self.order.line_ids:
            line.goods_id = goods
            line.onchange_goods_id()
            self.assertTrue(line.uom_id.name == u'件')
            wh_id = line.warehouse_dest_id.id
            self.assertTrue(wh_id == goods.default_wh.id)

            # 测试价格是否是商品的成本
            self.assertTrue(line.price == goods.cost)
            # 测试不设置商品的成本时是否弹出警告
            goods.cost = 0.0
            with self.assertRaises(except_orm):
                line.onchange_goods_id()

    def test_onchange_discount_rate(self):
        ''' 订单行优惠率改变时，改变优惠金额'''
        for line in self.order.line_ids:
            line.price = 10
            line.discount_rate = 10
            line.onchange_discount_rate()
            self.assertTrue(line.discount_amount == 10)


class test_buy_receipt(TransactionCase):

    def setUp(self):
        super(test_buy_receipt, self).setUp()
        self.order = self.env.ref('buy.buy_order_1')
        self.order.buy_order_done()
        self.receipt = self.env['buy.receipt'].search(
                       [('order_id', '=', self.order.id)])
        self.return_receipt = self.env.ref('buy.buy_receipt_return_1')
        warehouse_obj = self.env.ref('warehouse.wh_in_whin0')
        warehouse_obj.approve_order()

    def test_compute_all_amount(self):
        '''测试当优惠金额改变时，改变优惠后金额和本次欠款'''
        self.receipt.discount_amount = 5
        self.assertTrue(self.receipt.amount == 580)

    def test_get_buy_money_state(self):
        '''测试返回付款状态'''
        self.receipt._get_buy_money_state()
        self.receipt.buy_receipt_done()
        self.return_receipt._get_buy_return_state()
        self.assertTrue(self.receipt.money_state == u'未付款')
        self.receipt._get_buy_money_state()
        self.receipt.payment = self.receipt.amount - 1
        self.receipt._get_buy_money_state()
        self.assertTrue(self.receipt.money_state == u'部分付款')
        self.receipt.payment = self.receipt.amount
        self.receipt._get_buy_money_state()
        self.assertTrue(self.receipt.money_state == u'全部付款')

    def test_get_buy_return_state(self):
        '''测试返回退款状态'''
        self.return_receipt._get_buy_return_state()
        self.return_receipt.buy_receipt_done()
        self.return_receipt._get_buy_return_state()
        self.assertTrue(self.return_receipt.return_state == u'未退款')
        self.return_receipt._get_buy_money_state()
        self.return_receipt.payment = self.return_receipt.amount - 1
        self.return_receipt._get_buy_money_state()
        self.assertTrue(self.return_receipt.return_state == u'部分退款')
        self.return_receipt.payment = self.return_receipt.amount
        self.return_receipt._get_buy_money_state()
        self.assertTrue(self.return_receipt.return_state == u'全部退款')

    def test_onchange_discount_rate(self):
        '''测试优惠率改变时，优惠金额改变'''
        self.receipt.discount_rate = 10
        self.receipt.onchange_discount_rate()
        self.assertTrue(self.receipt.amount == 526.5)
        self.return_receipt.discount_rate = 10
        self.return_receipt.onchange_discount_rate()
        self.assertTrue(self.receipt.amount == 526.5)

    def test_create(self):
        '''创建采购入库单时生成有序编号'''
        receipt = self.env['buy.receipt'].create({
                                        })
        self.assertTrue(receipt.origin == 'buy.receipt.buy')
        receipt = self.env['buy.receipt'].with_context({
                                        'is_return': True
                                        }).create({
                                        })
        self.assertTrue(receipt.origin == 'buy.receipt.return')

    def test_unlink(self):
        '''测试删除采购入库/退货单'''
        # 测试是否可以删除已审核的单据
        self.receipt.buy_receipt_done()
        with self.assertRaises(except_orm):
            self.receipt.unlink()

        # 反审核购货订单，测试删除buy_receipt时是否可以删除关联的wh.move.line记录
        order = self.order.copy()
        order.buy_order_done()

        receipt = self.env['buy.receipt'].search(
                       [('order_id', '=', order.id)])
        move_id = receipt.buy_move_id.id
        order.buy_order_draft()
        move = self.env['wh.move'].search(
               [('id', '=', move_id)])
        self.assertTrue(not move)
        self.assertTrue(not move.line_in_ids)

    def test_buy_receipt_done(self):
        '''测试审核采购入库单/退货单，更新本单的付款状态/退款状态，并生成源单和付款单'''
        # 结算账户余额
        bank_account = self.env.ref('core.alipay')
        bank_account.write({'balance': 1000000, })
        receipt = self.receipt.copy()
        # 付款额不为空时，请选择结算账户
        self.receipt.payment = 100
        with self.assertRaises(except_orm):
            self.receipt.buy_receipt_done()
        # 结算账户不为空时，需要输入付款额！
        self.receipt.bank_account_id = bank_account
        self.receipt.payment = 0
        with self.assertRaises(except_orm):
            self.receipt.buy_receipt_done()
        # 付款金额不能大于折后金额！
        self.receipt.bank_account_id = bank_account
        self.receipt.payment = 20000
        with self.assertRaises(except_orm):
            self.receipt.buy_receipt_done()
        # 重复审核报错
        self.receipt.bank_account_id = None
        self.receipt.payment = 0
        self.receipt.buy_receipt_done()
        with self.assertRaises(except_orm):
            self.receipt.buy_receipt_done()
        self.return_receipt.buy_receipt_done()
        with self.assertRaises(except_orm):
            self.return_receipt.buy_receipt_done()
        # 入库单上的采购费用分摊到入库单明细行上
        receipt.cost_line_ids.create({
                          'buy_id': receipt.id,
                          'partner_id': 4,
                          'amount': 100, })
        # 测试分摊之前审核是否会弹出警告
        with self.assertRaises(except_orm):
            receipt.buy_receipt_done()
        # 测试分摊之后金额是否相等，然后审核，测试采购费用是否产生源单
        receipt.buy_share_cost()
        receipt.buy_receipt_done()
        for line in receipt.line_in_ids:
            self.assertTrue(line.share_cost == 100)
            self.assertTrue(line.using_attribute)
