# -*- coding: utf-8 -*-
from openerp.tests.common import TransactionCase
from openerp.exceptions import except_orm


class test_buy_order(TransactionCase):

    def setUp(self):
        super(test_buy_order, self).setUp()
        self.order = self.env.ref('buy.buy_order_1')
        self.order.bank_account_id = False

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
        '''新建购货订单时调入仓库的默认值'''
        order = self.env['buy.order'].with_context({
             'warehouse_dest_type': 'stock'
             }).create({})
        # 验证明细行上仓库是否是购货订单上调入仓库
        hd_stock = self.browse_ref('warehouse.hd_stock')
        order.warehouse_dest_id = hd_stock
        line = order.line_ids.with_context({
            'default_warehouse_dest_id': order.warehouse_dest_id}).create({
            'order_id': order.id})
        self.assertTrue(line.warehouse_dest_id == hd_stock)
        self.env['buy.order'].create({})

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
        # 未填数量应报错
        self.order.buy_order_draft()
        for line in self.order.line_ids:
            line.quantity = 0
        with self.assertRaises(except_orm):
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
        with self.assertRaises(except_orm):
            self.order.buy_order_done()
        # 结算账户不为空时，需要输入预付款！
        self.order.bank_account_id = bank_account
        self.order.prepayment = 0
        with self.assertRaises(except_orm):
            self.order.buy_order_done()

        # 没有订单行时审核报错
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

    def test_compute_using_attribute(self):
        '''返回订单行中产品是否使用属性'''
        for line in self.order.line_ids:
            self.assertTrue(line.using_attribute)
            line.goods_id = self.env.ref('goods.mouse')
            self.assertTrue(not line.using_attribute)

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
        '''当订单行的产品变化时，带出产品上的单位、成本'''
        goods = self.env.ref('goods.cable')
        goods.default_wh = self.env.ref('warehouse.hd_stock').id
        for line in self.order.line_ids:
            line.goods_id = goods
            line.onchange_goods_id()
            self.assertTrue(line.uom_id.name == u'件')

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
        self.order.bank_account_id = False
        self.order.buy_order_done()
        self.receipt = self.env['buy.receipt'].search(
                       [('order_id', '=', self.order.id)])
        self.return_receipt = self.env.ref('buy.buy_receipt_return_1')
        warehouse_obj = self.env.ref('warehouse.wh_in_whin0')
        warehouse_obj.approve_order()

        self.bank_account = self.env.ref('core.alipay')
        self.bank_account.balance = 10000

    def test_compute_all_amount(self):
        '''测试当优惠金额改变时，改变优惠后金额和本次欠款'''
        self.receipt.discount_amount = 5
        self.assertTrue(self.receipt.amount == 580)

    def test_get_buy_money_state(self):
        '''测试返回付款状态'''
        self.receipt.buy_receipt_done()
        self.receipt._get_buy_money_state()
        self.assertTrue(self.receipt.money_state == u'未付款')

        receipt = self.receipt.copy()
        receipt.payment = receipt.amount - 1
        receipt.bank_account_id = self.bank_account
        receipt.buy_receipt_done()
        receipt._get_buy_money_state()
        self.assertTrue(receipt.money_state == u'部分付款')

        receipt = self.receipt.copy()
        receipt.payment = receipt.amount
        receipt.bank_account_id = self.bank_account
        receipt.buy_receipt_done()
        receipt._get_buy_money_state()
        self.assertTrue(receipt.money_state == u'全部付款')

    def test_get_buy_return_state(self):
        '''测试返回退款状态'''
        self.return_receipt._get_buy_return_state()
        self.return_receipt.buy_receipt_done()
        self.return_receipt._get_buy_return_state()
        self.assertTrue(self.return_receipt.return_state == u'未退款')

        return_receipt = self.return_receipt.copy()
        return_receipt.payment = return_receipt.amount - 1
        return_receipt.bank_account_id = self.bank_account
        return_receipt.buy_receipt_done()
        return_receipt._get_buy_return_state()
        self.assertTrue(return_receipt.return_state == u'部分退款')

        return_receipt = self.return_receipt.copy()
        return_receipt.payment = return_receipt.amount
        return_receipt.bank_account_id = self.bank_account
        return_receipt.buy_receipt_done()
        return_receipt._get_buy_return_state()
        self.assertTrue(return_receipt.return_state == u'全部退款')

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
        # 入库单审核时未填数量应报错
        for line in self.receipt.line_in_ids:
            line.goods_qty = 0
        with self.assertRaises(except_orm):
            self.receipt.buy_receipt_done()
        # 采购退货单审核时未填数量应报错
        for line in self.return_receipt.line_out_ids:
            line.goods_qty = 0
        with self.assertRaises(except_orm):
            self.return_receipt.buy_receipt_done()
        # 重复审核入库单报错
        self.receipt.bank_account_id = None
        self.receipt.payment = 0
        for line in self.receipt.line_in_ids:
            line.goods_qty = 1
        self.receipt.buy_receipt_done()
        with self.assertRaises(except_orm):
            self.receipt.buy_receipt_done()
        # 重复审核退货单报错
        for line in self.return_receipt.line_out_ids:
            line.goods_qty = 1
        self.return_receipt.buy_receipt_done()
        with self.assertRaises(except_orm):
            self.return_receipt.buy_receipt_done()
        # 入库单上的采购费用分摊到入库单明细行上
        receipt.cost_line_ids.create({
                          'buy_id': receipt.id,
                          'category_id':self.env.ref('core.cat_consult').id,
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

    def test_scan_barcode(self):
        '''采购扫码出入库'''
        warehouse = self.env['wh.move']
        barcode = '12345678987'
        model_name = 'buy.receipt'
        #采购出库单扫码
        buy_order_return = self.env.ref('buy.buy_receipt_return_1')
        warehouse.scan_barcode(model_name,barcode,buy_order_return.id)
        warehouse.scan_barcode(model_name,barcode,buy_order_return.id)
        #采购入库单扫码
        warehouse.scan_barcode(model_name,barcode,self.receipt.id)
        warehouse.scan_barcode(model_name,barcode,self.receipt.id)


class test_wh_move_line(TransactionCase):

    def setUp(self):
        '''准备基本数据'''
        super(test_wh_move_line, self).setUp()
        self.order = self.env.ref('buy.buy_order_1')
        self.order.bank_account_id = False
        self.order.buy_order_done()
        self.receipt = self.env['buy.receipt'].search(
                       [('order_id', '=', self.order.id)])
        self.return_receipt = self.env.ref('buy.buy_receipt_return_1')

        self.goods_mouse = self.browse_ref('goods.mouse')

    def test_onchange_goods_id(self):
        '''测试采购模块中商品的onchange,是否会带出默认库位和单价'''
        # 入库单行：修改鼠标成本为0，测试是否报错
        self.goods_mouse.cost = 0.0
        for line in self.receipt.line_in_ids:
            line.goods_id = self.goods_mouse.id
            with self.assertRaises(except_orm):
                line.onchange_goods_id()

        # 采购退货单行
        for line in self.return_receipt.line_out_ids:
            line.goods_id.cost = 0.0
            with self.assertRaises(except_orm):
                line.with_context({'default_is_return': True,
                    'default_partner': self.return_receipt.partner_id.id}).onchange_goods_id()
            line.goods_id.cost = 1.0
            line.with_context({'default_is_return': True,
                'default_partner': self.return_receipt.partner_id.id}).onchange_goods_id()
