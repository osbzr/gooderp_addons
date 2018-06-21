# -*- coding: utf-8 -*-
from odoo.tests.common import TransactionCase
from odoo.exceptions import UserError


class TestBuyReceipt(TransactionCase):

    def setUp(self):
        super(TestBuyReceipt, self).setUp()
        self.env.ref('core.goods_category_1').account_id = self.env.ref(
            'finance.account_goods').id
        self.order = self.env.ref('buy.buy_order_1')
        self.order.bank_account_id = False
        self.order.buy_order_done()
        self.receipt = self.env['buy.receipt'].search(
            [('order_id', '=', self.order.id)])
        self.return_receipt = self.env.ref('buy.buy_receipt_return_1')
        self.env.ref('warehouse.wh_in_whin0').date = '2016-02-06'
        warehouse_obj = self.env.ref('warehouse.wh_in_whin0')
        warehouse_obj.approve_order()

        self.bank_account = self.env.ref('core.alipay')
        self.bank_account.balance = 10000

        # 因同一个业务伙伴不能存在两张未审核的收付款单，把系统里已有的相关业务伙伴未审核的收付款单审核
        self.env.ref('money.get_40000').money_order_done()
        self.env.ref('money.pay_2000').money_order_done()

    def test_compute_all_amount(self):
        '''测试当优惠金额改变时，改变成交金额'''
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
        # 查找产生的付款单，并审核
        source_line = self.env['source.order.line'].search(
            [('name', '=', receipt.invoice_id.id)])
        for line in source_line:
            line.money_id.money_order_done()
        # 判断状态
        receipt._get_buy_money_state()
        self.assertTrue(receipt.money_state == u'部分付款')

        receipt = self.receipt.copy()
        receipt.payment = receipt.amount
        receipt.bank_account_id = self.bank_account
        receipt.buy_receipt_done()
        # 查找产生的付款单，并审核
        source_line = self.env['source.order.line'].search(
            [('name', '=', receipt.invoice_id.id)])
        for line in source_line:
            line.money_id.money_order_done()
        # 判断状态
        receipt._get_buy_money_state()
        self.assertTrue(receipt.money_state == u'全部付款')

    def test_get_buy_money_state_return(self):
        '''测试返回退款状态'''
        self.return_receipt._get_buy_money_state()
        self.return_receipt.buy_receipt_done()
        self.return_receipt._get_buy_money_state()
        self.assertTrue(self.return_receipt.return_state == u'未退款')

        return_receipt = self.return_receipt.copy()
        return_receipt.payment = return_receipt.amount - 1
        return_receipt.bank_account_id = self.bank_account
        return_receipt.buy_receipt_done()
        # 查找产生的付款单，并审核
        source_line = self.env['source.order.line'].search(
            [('name', '=', return_receipt.invoice_id.id)])
        for line in source_line:
            line.money_id.money_order_done()
        # 判断状态
        return_receipt._get_buy_money_state()
        self.assertTrue(return_receipt.return_state == u'部分退款')

        return_receipt = self.return_receipt.copy()
        return_receipt.payment = return_receipt.amount
        return_receipt.bank_account_id = self.bank_account
        return_receipt.buy_receipt_done()
        # 查找产生的付款单，并审核
        source_line = self.env['source.order.line'].search(
            [('name', '=', return_receipt.invoice_id.id)])
        for line in source_line:
            line.money_id.money_order_done()
        # 判断状态
        return_receipt._get_buy_money_state()
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
        with self.assertRaises(UserError):
            self.receipt.unlink()

        # 反审核购货订单，测试删除buy_receipt时是否可以删除关联的wh.move.line记录
        self.receipt.buy_receipt_draft()

        move_id = self.receipt.buy_move_id.id
        self.order.buy_order_draft()
        move = self.env['wh.move'].search(
            [('id', '=', move_id)])
        self.assertTrue(not move)
        self.assertTrue(not move.line_in_ids)

    def test_buy_receipt_done(self):
        '''审核采购入库单/退货单，更新本单的付款状态/退款状态，并生成结算单和付款单'''
        # 结算账户余额
        bank_account = self.env.ref('core.alipay')
        bank_account.write({'balance': 1000000, })
        receipt = self.receipt.copy()
        # 付款额不为空时，请选择结算账户
        self.receipt.payment = 100
        with self.assertRaises(UserError):
            self.receipt.buy_receipt_done()
        # 付款金额不能大于折后金额！
        self.receipt.bank_account_id = bank_account
        self.receipt.payment = 20000
        with self.assertRaises(UserError):
            self.receipt.buy_receipt_done()
        # 入库单审核时未填数量应报错
        for line in self.receipt.line_in_ids:
            line.goods_qty = 0
        with self.assertRaises(UserError):
            self.receipt.buy_receipt_done()
        # 采购退货单审核时未填数量应报错
        for line in self.return_receipt.line_out_ids:
            line.goods_qty = 0
        with self.assertRaises(UserError):
            self.return_receipt.buy_receipt_done()
        # 重复审核入库单报错
        self.receipt.bank_account_id = None
        self.receipt.payment = 0
        for line in self.receipt.line_in_ids:
            line.goods_qty = 1
        self.receipt.buy_receipt_done()
        with self.assertRaises(UserError):
            self.receipt.buy_receipt_done()
        # 重复审核退货单报错
        for line in self.return_receipt.line_out_ids:
            line.goods_qty = 1
        self.return_receipt.buy_receipt_done()
        with self.assertRaises(UserError):
            self.return_receipt.buy_receipt_done()
        # 入库单上的采购费用分摊到入库单明细行上
        receipt.cost_line_ids.create({
            'buy_id': receipt.id,
            'category_id': self.env.ref('core.cat_consult').id,
            'partner_id': 4,
            'amount': 100, })
        # 测试分摊之前审核是否会弹出警告
        with self.assertRaises(UserError):
            receipt.buy_receipt_done()
        # 测试分摊之后金额是否相等，然后审核，测试采购费用是否产生结算单
        receipt.buy_share_cost()
        receipt.buy_receipt_done()
        for line in receipt.line_in_ids:
            self.assertTrue(line.share_cost == 100)
            self.assertTrue(line.using_attribute)

    def test_wrong_receipt_done_lot_unique_current(self):
        '''审核时，当前入库单行之间同一商品批号不能相同'''
        receipt = self.env['buy.receipt'].create({
            'partner_id': self.env.ref('core.lenovo').id,
            'date': '2016-09-01',
            'date_due': '2016-09-05',
            'warehouse_dest_id': self.env.ref('warehouse.bj_stock').id,
            'line_in_ids': [
                (0, 0, {
                    'goods_id': self.env.ref('goods.mouse').id,
                    'lot': 'lot_1',
                    'goods_qty': 1.0}),
                (0, 0, {
                    'goods_id': self.env.ref('goods.mouse').id,
                    'lot': 'lot_1',
                    'goods_qty': 1.0})
            ]
        })
        with self.assertRaises(UserError):
            receipt.buy_receipt_done()

    def test_wrong_receipt_done_lot_unique_wh(self):
        '''审核时，当前入库单行与仓库里同一商品批号不能相同'''
        receipt = self.env['buy.receipt'].create({
            'partner_id': self.env.ref('core.lenovo').id,
            'date': '2016-09-01',
            'date_due': '2016-09-05',
            'warehouse_dest_id': self.env.ref('warehouse.bj_stock').id,
            'line_in_ids': [(0, 0, {
                'goods_id': self.env.ref('goods.mouse').id,
                'lot': 'lot_1',
                'goods_qty': 1.0,
                'state': 'done'})]
        })
        with self.assertRaises(UserError):
            receipt.buy_receipt_done()

    def test_wrong_receipt_done_amount_less_than_zero(self):
        ''' 测试 购货/退货金额不能小于 0 '''
        for line in self.receipt.line_in_ids:  # 购货金额不能小于 0
            line.price_taxed = 0.0
            line.cost_unit = 0.0
            line.discount_amount = 10.0
        with self.assertRaises(UserError):
            self.receipt.buy_receipt_done()

        for line in self.return_receipt.line_out_ids:  # 退货金额不能小于 0
            line.price_taxed = 0.0
            line.cost_unit = 0.0
            line.discount_amount = 10.0
        with self.assertRaises(UserError):
            self.return_receipt.buy_receipt_done()

    def test_receipt_done_no_voucher(self):
        ''' 测试 采购入库单  没有凭证行 删除凭证 '''
        for line in self.receipt.line_in_ids:
            line.price_taxed = 0.0
            line.cost_unit = 0.0
        self.receipt.buy_receipt_done()

    def test_receipt_make_invoice(self):
        '''审核入库单：不勾按收货结算时'''
        self.order.buy_order_draft()
        self.order.invoice_by_receipt = False
        self.order.buy_order_done()
        receipt = self.env['buy.receipt'].search(
            [('order_id', '=', self.order.id)])
        receipt.buy_receipt_done()

    def test_buy_receipt_draft(self):
        '''反审核采购入库单/退货单'''
        # 先审核入库单，再反审核
        self.receipt.bank_account_id = self.bank_account.id
        self.receipt.payment = 100
        for line in self.receipt.line_in_ids:
            line.goods_qty = 2
        self.receipt.buy_receipt_done()
        # 修改入库单，再次审核，并不产生分单
        self.receipt.buy_receipt_draft()
        for line in self.receipt.line_in_ids:
            line.goods_qty = 3
        self.receipt.buy_receipt_done()
        receipt = self.env['buy.receipt'].search(
            [('order_id', '=', self.order.id)])
        self.assertTrue(len(receipt) == 2)

    def test_buy_receipt_draft_handle_money_order(self):
        '''buy receipt_draft: handle money order in different situations'''
        # 先审核入库单，再反审核
        self.receipt.bank_account_id = self.bank_account.id
        self.receipt.payment = 100
        for line in self.receipt.line_in_ids:
            line.goods_qty = 2
        self.receipt.buy_receipt_done()
        # 修改入库单，再次审核，并不产生分单
        self.receipt.buy_receipt_draft()
        for line in self.receipt.line_in_ids:
            line.goods_qty = 3
        self.receipt.buy_receipt_done()
        receipts = self.env['buy.receipt'].search(
            [('order_id', '=', self.order.id)])
        for receipt in receipts:
            if receipt.state != 'done':
                receipt.buy_receipt_done()

        money_orders = self.env['money.order'].search([('partner_id', '=', self.env.ref('core.lenovo').id),
                                                       ('state', '=', 'draft')])
        for m in money_orders:
            m.money_order_done()

        # 建入库单对应的付款单
        money_order = self.env['money.order'].with_context({'type': 'pay'}).create({
            'partner_id': self.env.ref('core.lenovo').id,
            'line_ids': [(0, 0, {
                'bank_id': self.env.ref('core.comm').id,
                'amount': 300.0})]
        })
        money_order.onchange_partner_id()
        # 反审核采购入库单
        receipts and receipts[0].buy_receipt_draft()  # 付款单 源单行 有别的行存在
        len(receipts) > 1 and receipts[1].buy_receipt_draft()  # 付款单 源单行 不存在别的行

    def test_buy_receipt_draft_quantity_in(self):
        '''反审核入库单时，回写购货订单行已执行数量'''
        # 退货类型的购货订单生成的采购退货单的反审核
        self.receipt.buy_receipt_done()
        order = self.env.ref('buy.buy_return_order_1')
        # order.bank_account_id = False
        order.buy_order_done()
        return_receipt = self.env['buy.receipt'].search(
            [('order_id', '=', order.id)])
        return_receipt.buy_receipt_done()
        return_receipt.buy_receipt_draft()
        self.assertEqual(return_receipt.line_out_ids[0].buy_line_id.quantity_in, 0.0)

        # 购货类型的购货订单生成的采购入库单，生成退货单的反审核
        return_dict = self.receipt.buy_to_return()
        return_order = self.env['buy.receipt'].search(
            [('id', '=', return_dict['res_id'])])
        return_order.line_out_ids[0].goods_qty = 3
        return_order.buy_receipt_done()
        return_order.buy_receipt_draft()
        self.assertEqual(return_order.line_out_ids[0].buy_line_id.quantity_in, 10.0)

    def test_buy_receipt_draft_twice(self):
        '''两次审核和反审核应报错'''
        with self.assertRaises(UserError):
            self.receipt.buy_receipt_draft()
        self.receipt.buy_receipt_done()
        with self.assertRaises(UserError):
            self.receipt.buy_receipt_done()

    def test_scan_barcode(self):
        '''采购扫码出入库'''
        warehouse = self.env['wh.move']
        barcode = '12345678987'
        model_name = 'buy.receipt'
        # 采购出库单扫码
        buy_order_return = self.env.ref('buy.buy_receipt_return_1')
        warehouse.scan_barcode(model_name, barcode, buy_order_return.id)
        warehouse.scan_barcode(model_name, barcode, buy_order_return.id)
        # 采购入库单扫码
        warehouse.scan_barcode(model_name, barcode, self.receipt.id)
        warehouse.scan_barcode(model_name, barcode, self.receipt.id)

        # 商品的条形码扫码出入库
        barcode = '123456789'
        # 采购入库单扫码
        warehouse.scan_barcode(model_name, barcode, self.receipt.id)
        warehouse.scan_barcode(model_name, barcode, self.receipt.id)
        # 采购退货单扫码
        buy_order_return = self.env.ref('buy.buy_receipt_return_1')
        warehouse.scan_barcode(model_name, barcode, buy_order_return.id)
        warehouse.scan_barcode(model_name, barcode, buy_order_return.id)

    def test_onchange_partner_id(self):
        ''' 测试 改变 partner, 入库单行商品税率变化 '''
        # partner 无 税率，入库单行商品无税率
        self.env.ref('core.lenovo').tax_rate = 0
        self.env.ref('goods.keyboard').tax_rate = 0
        self.receipt.onchange_partner_id()
        # partner 有 税率，入库单行商品无税率
        self.env.ref('core.lenovo').tax_rate = 10
        self.env.ref('goods.keyboard').tax_rate = 0
        self.receipt.onchange_partner_id()
        # partner 无税率，入库单行商品无税率
        self.env.ref('core.lenovo').tax_rate = 0
        self.env.ref('goods.keyboard').tax_rate = 10
        self.receipt.onchange_partner_id()
        # partner 税率 > 入库单行商品税率
        self.env.ref('core.lenovo').tax_rate = 11
        self.env.ref('goods.keyboard').tax_rate = 10
        self.receipt.onchange_partner_id()
        # partner 税率 =< 入库单行商品税率
        self.env.ref('core.lenovo').tax_rate = 11
        self.env.ref('goods.keyboard').tax_rate = 12
        self.receipt.onchange_partner_id()

    def test_buy_receipt_done_currency(self):
        """入库单选择外币时审核"""
        self.order.buy_order_draft()
        self.order.currency_id = self.env.ref('base.USD')
        for line in self.order.line_ids:
            line.tax_rate = 0
        self.order.buy_order_done()
        self.receipt = self.env['buy.receipt'].search(
            [('order_id', '=', self.order.id)])
        self.receipt.buy_receipt_done()

    def test_buy_to_return(self):
        '''采购入库单转化为采购退货单'''
        self.receipt.line_in_ids[0].copy()
        self.receipt.buy_receipt_done()
        self.receipt.buy_to_return()
        with self.assertRaises(UserError):
            self.receipt.buy_to_return()

        # 该订单已全部退货，再次点击按钮则报错
        return_order = self.env['buy.receipt'].search([
            ('is_return', '=', True),
            ('origin_id', '=', self.receipt.id),
        ])
        return_order.buy_receipt_done()
        with self.assertRaises(UserError):
            self.receipt.buy_to_return()

    def test_buy_to_return_using_batch(self):
        ''' 采购入库单转化为采购退货单:订单行产品进行了批次管理 '''
        self.receipt.line_in_ids[0].goods_id.using_batch = True
        self.receipt.line_in_ids[0].lot = '1'
        self.receipt.line_in_ids[0].copy()
        self.receipt.buy_receipt_done()
        self.receipt.buy_to_return()

    def test_buy_receipt_done_return_order_has_payment(self):
        ''' 有付款的采购退货单 系统认为是纯退货，不再生成草稿状态的发货单 '''
        self.receipt.line_in_ids[0].copy()
        self.receipt.buy_receipt_done()
        self.receipt.buy_to_return()

        return_order = self.env['buy.receipt'].search([
                    ('is_return', '=', True),
                    ('origin_id', '=', self.receipt.id),
                ])
        return_order.payment = 2
        return_order.bank_account_id = self.bank_account.id
        return_order.buy_receipt_done()



class TestWhMoveLine(TransactionCase):

    def setUp(self):
        '''准备基本数据'''
        super(TestWhMoveLine, self).setUp()
        self.order = self.env.ref('buy.buy_order_1')
        self.order.bank_account_id = False
        self.order.buy_order_done()
        self.receipt = self.env['buy.receipt'].search(
            [('order_id', '=', self.order.id)])
        self.return_receipt = self.env.ref('buy.buy_receipt_return_1')

        self.goods_mouse = self.browse_ref('goods.mouse')

    def test_onchange_goods_id(self):
        '''测试采购模块中商品的onchange,是否会带出单价'''
        for line in self.receipt.line_in_ids:
            line.onchange_goods_id()

        # 采购退货单行
        for line in self.return_receipt.line_out_ids:
            line.goods_id.cost = 1.0
            line.with_context({'default_is_return': True,
                               'default_partner': self.return_receipt.partner_id.id}).onchange_goods_id()

    def test_onchange_goods_id_tax_rate(self):
        ''' 测试 修改商品时，入库单行税率变化 '''
        self.receipt.partner_id = self.env.ref('core.lenovo')
        for order_line in self.receipt.line_in_ids:
            # partner 无 税率，入库单行商品无税率
            self.env.ref('core.lenovo').tax_rate = 0
            self.env.ref('goods.keyboard').tax_rate = 0
            order_line.with_context(
                {'default_partner': self.receipt.partner_id.id}).onchange_goods_id()
            # partner 有 税率，入库单行商品无税率
            self.env.ref('core.lenovo').tax_rate = 10
            self.env.ref('goods.keyboard').tax_rate = 0
            order_line.with_context(
                {'default_partner': self.receipt.partner_id.id}).onchange_goods_id()
            # partner 无税率，入库单行商品有税率
            self.env.ref('core.lenovo').tax_rate = 0
            self.env.ref('goods.keyboard').tax_rate = 10
            order_line.with_context(
                {'default_partner': self.receipt.partner_id.id}).onchange_goods_id()
            # partner 税率 > 入库单行商品税率
            self.env.ref('core.lenovo').tax_rate = 11
            self.env.ref('goods.keyboard').tax_rate = 10
            order_line.with_context(
                {'default_partner': self.receipt.partner_id.id}).onchange_goods_id()
            # partner 税率 =< 入库单行商品税率
            self.env.ref('core.lenovo').tax_rate = 9
            self.env.ref('goods.keyboard').tax_rate = 10
            order_line.with_context(
                {'default_partner': self.receipt.partner_id.id}).onchange_goods_id()
