# -*- coding: utf-8 -*-
from openerp.tests.common import TransactionCase
from openerp.exceptions import except_orm


class test_detail_wizard(TransactionCase):
    '''测试采购明细表向导'''

    def setUp(self):
        ''' 准备报表数据 '''
        super(test_detail_wizard, self).setUp()
        warehouse_obj = self.env.ref('warehouse.wh_in_whin0')
        warehouse_obj.approve_order()
        self.order = self.env.ref('buy.buy_order_1')
        self.order.bank_account_id = False
        self.order.buy_order_done()
        self.receipt = self.env['buy.receipt'].search(
                       [('order_id', '=', self.order.id)])
        self.receipt.bank_account_id = self.env.ref('core.comm')
        self.env.ref('money.get_40000').money_order_done()
        self.receipt.payment = 2.0
        self.receipt.buy_receipt_done()
        self.receipt_return = self.browse_ref('buy.buy_receipt_return_1')
        self.receipt_return.buy_receipt_done()
        self.detail_obj = self.env['buy.order.detail.wizard']
        self.detail = self.detail_obj.create({})
        # 退货订单审核生成退货单，退货单审核
        return_order = self.env.ref('buy.buy_return_order_1')
        return_order.bank_account_id = False
        return_order.buy_order_done()
        return_receipt = self.env['buy.receipt'].search(
                       [('order_id', '=', return_order.id)])
        return_receipt.buy_receipt_done()

    def test_button_ok(self):
        '''测试采购明细表确认按钮'''
        # 日期报错
        detail = self.detail_obj.create({
                             'date_start': '2016-11-01',
                             'date_end': '2016-1-01',
                             })
        with self.assertRaises(except_orm):
            detail.button_ok()
        # 按产品搜索
        self.detail.goods_id = self.env.ref('goods.mouse').id
        self.detail.button_ok()
        # 按供应商搜索
        self.detail.goods_id = False
        self.detail.partner_id = self.env.ref('core.lenovo').id
        self.detail.button_ok()
        # 按单据编号搜索
        self.detail.goods_id = False
        self.detail.partner_id = False
        self.detail.order_id = self.receipt.id
        self.detail.button_ok()
        # 按日期搜索
        self.detail.goods_id = False
        self.detail.partner_id = False
        self.detail.order_id = False
        self.detail.button_ok()

    def test_view_detail(self):
        '''查看明细按钮'''
        self.detail.button_ok()
        goods_id = self.env.ref('goods.keyboard').id
        detail_line = self.env['buy.order.detail'].search(
                                [('goods_id', '=', goods_id)])
        for line in detail_line:
            line.view_detail()


class test_track_wizard(TransactionCase):
    '''测试采购订单跟踪表向导'''

    def setUp(self):
        ''' 准备报表数据 '''
        super(test_track_wizard, self).setUp()
        warehouse_obj = self.env.ref('warehouse.wh_in_whin0')
        warehouse_obj.approve_order()
        self.order = self.env.ref('buy.buy_order_1')
        order_2 = self.order.copy()
        for line in order_2.line_ids:
            line.goods_id = self.env.ref('goods.mouse').id
        order_2.bank_account_id = False
        order_2.buy_order_done()
        receipt_2 = self.env['buy.receipt'].search(
                    [('order_id', '=', order_2.id)])
        for line in receipt_2.line_in_ids:
            line.goods_qty = 5
        receipt_2.buy_receipt_done()
        receipt_3 = self.env['buy.receipt'].search(
                    [('order_id', '=', order_2.id), ('state', '=', 'draft')])
        receipt_3.buy_receipt_done()
        self.order.bank_account_id = False
        self.order.buy_order_done()
        self.receipt = self.env['buy.receipt'].search(
                       [('order_id', '=', self.order.id)])
        self.receipt.bank_account_id = self.env.ref('core.comm')
        self.env.ref('money.get_40000').money_order_done()
        self.receipt.payment = 2.0
        self.receipt.buy_receipt_done()
        self.receipt_return = self.browse_ref('buy.buy_receipt_return_1')
        self.receipt_return.buy_receipt_done()
        self.track_obj = self.env['buy.order.track.wizard']
        self.track = self.track_obj.create({})

    def test_button_ok(self):
        '''测试采购订单跟踪表确认按钮'''
        # 日期报错
        track = self.track_obj.create({
                             'date_start': '2016-11-01',
                             'date_end': '2016-1-01',
                             })
        with self.assertRaises(except_orm):
            track.button_ok()
        # 按产品搜索
        self.track.goods_id = self.env.ref('goods.mouse').id
        self.track.button_ok()
        # 按供应商搜索
        self.track.goods_id = False
        self.track.partner_id = self.env.ref('core.lenovo').id
        self.track.button_ok()
        # 按订单号搜索
        self.track.goods_id = False
        self.track.partner_id = False
        self.track.order_id = self.order.id
        self.track.button_ok()
        # 按日期搜索
        self.track.goods_id = False
        self.track.partner_id = False
        self.track.order_id = False
        self.track.button_ok()

    def test_view_detail(self):
        '''查看明细按钮'''
        self.track.button_ok()
        goods_id = self.env.ref('goods.cable').id
        track_line = self.env['buy.order.track'].search([('goods_id', '=', goods_id)])
        track_line[0].view_detail()


class test_payment_wizard(TransactionCase):
    '''测试采购付款一览表向导'''

    def setUp(self):
        ''' 准备报表数据 '''
        super(test_payment_wizard, self).setUp()
        warehouse_obj = self.env.ref('warehouse.wh_in_whin0')
        warehouse_obj.approve_order()
        self.order = self.env.ref('buy.buy_order_1')
        self.order.bank_account_id = False
        self.order.buy_order_done()
        self.receipt = self.env['buy.receipt'].search(
                       [('order_id', '=', self.order.id)])
        self.receipt.bank_account_id = self.env.ref('core.comm')
        self.env.ref('money.get_40000').money_order_done()
        self.receipt.payment = 2.0
        new_receipt = self.receipt.copy()
        new_receipt.discount_amount = 585   # 使入库单的优惠后金额为0
        new_receipt.payment = 0
        new_receipt.bank_account_id = False
        new_receipt.buy_receipt_done()
        self.receipt.buy_receipt_done()
        self.receipt_return = self.browse_ref('buy.buy_receipt_return_1')
        self.receipt_return.buy_receipt_done()
        self.payment_obj = self.env['buy.payment.wizard']
        self.payment = self.payment_obj.create({})

    def test_button_ok(self):
        '''测试采购付款一览表确认按钮'''
        # 日期报错
        payment = self.payment_obj.create({
                             'date_start': '2016-11-01',
                             'date_end': '2016-1-01',
                             })
        with self.assertRaises(except_orm):
            payment.button_ok()
        # 按供应商类别,供应商，采购单号搜索
        s_category_id = self.env.ref('core.supplier_category_1').id
        self.payment.s_category_id = s_category_id
        self.payment.partner_id = self.env.ref('core.lenovo').id
        self.payment.order_id = self.env.ref('buy.buy_order_1').id
        self.payment.button_ok()
        # 按日期搜索
        self.payment.s_category_id = False
        self.payment.partner_id = False
        self.payment.order_id = False
        self.payment.button_ok()

    def test_view_detail(self):
        '''查看明细按钮'''
        self.payment.button_ok()
        payment_line = self.env['buy.payment'].search(
                                [('order_name', '=', self.receipt.name)])
        for line in payment_line:
            line.view_detail()
        payment_line2 = self.env['buy.payment'].search(
                                [('order_name', '=', self.receipt_return.name)])
        for line in payment_line2:
            line.view_detail()


class test_goods_wizard(TransactionCase):
    '''测试采购汇总表（按商品）向导'''

    def setUp(self):
        ''' 准备报表数据 '''
        super(test_goods_wizard, self).setUp()
        warehouse_obj = self.env.ref('warehouse.wh_in_whin0')
        warehouse_obj.approve_order()
        self.order = self.env.ref('buy.buy_order_1')
        self.order.bank_account_id = False
        self.order.buy_order_done()
        self.receipt = self.env['buy.receipt'].search(
                       [('order_id', '=', self.order.id)])
        self.receipt.bank_account_id = self.env.ref('core.comm')
        self.env.ref('money.get_40000').money_order_done()
        self.receipt.payment = 2.0
        self.receipt.buy_receipt_done()
        self.receipt_return = self.browse_ref('buy.buy_receipt_return_1')
        self.receipt_return.buy_receipt_done()
        self.goods_wizard_obj = self.env['buy.summary.goods.wizard']
        self.goods_wizard = self.goods_wizard_obj.create({})

        self.goods_mouse = self.env.ref('goods.mouse')
        self.core_lenovo = self.env.ref('core.lenovo')
        self.goods_categ = self.env.ref('core.goods_category_1')

    def test_button_ok(self):
        '''采购汇总表（按商品）向导确认按钮'''
        # 日期报错
        goods_wizard = self.goods_wizard_obj.create({
                             'date_start': '2016-11-01',
                             'date_end': '2016-1-01',
                             })
        with self.assertRaises(except_orm):
            goods_wizard.button_ok()
        # 按商品搜索
        self.goods_wizard.goods_id = self.goods_mouse.id
        self.goods_wizard.button_ok()
        # 按供应商搜索
        self.goods_wizard.goods_id = False
        self.goods_wizard.partner_id = self.core_lenovo.id
        self.goods_wizard.button_ok()
        # 按商品类别搜索
        self.goods_wizard.goods_id = False
        self.goods_wizard.partner_id = False
        self.goods_wizard.goods_categ_id = self.goods_categ.id
        self.goods_wizard.button_ok()
        # 按日期搜索
        self.goods_wizard.goods_id = False
        self.goods_wizard.partner_id = False
        self.goods_wizard.goods_categ_id = False
        self.goods_wizard.button_ok()

    def test_goods_report(self):
        '''测试采购汇总表（按商品）报表'''
        summary_goods = self.env['buy.summary.goods'].create({})
        context = self.goods_wizard.button_ok().get('context')
        results = summary_goods.with_context(context).search_read(domain=[])
        new_wizard = self.goods_wizard.copy()
        new_wizard.goods_id = self.goods_mouse.id
        new_wizard.partner_id = self.core_lenovo.id
        new_wizard.goods_categ_id = self.goods_categ.id
        new_context = new_wizard.button_ok().get('context')
        new_results = summary_goods.with_context(new_context).search_read(
                                                                  domain=[])
        self.assertEqual(len(results), 2)
        self.assertEqual(len(new_results), 0)

    def test_view_detail(self):
        '''采购汇总表（按商品）  查看明细按钮'''
        summary_goods = self.env['buy.summary.goods'].create({})
        context = self.goods_wizard.button_ok().get('context')
        results = summary_goods.with_context(context).search_read(domain=[])
        for line in results:
            summary_line = summary_goods.browse(line['id'])
            summary_line.with_context(context).view_detail()


class test_partner_wizard(TransactionCase):
    '''测试采购汇总表（按供应商）向导'''

    def setUp(self):
        ''' 准备报表数据 '''
        super(test_partner_wizard, self).setUp()
        warehouse_obj = self.env.ref('warehouse.wh_in_whin0')
        warehouse_obj.approve_order()
        self.order = self.env.ref('buy.buy_order_1')
        self.order.bank_account_id = False
        self.order.buy_order_done()
        self.receipt = self.env['buy.receipt'].search(
                       [('order_id', '=', self.order.id)])
        self.receipt.bank_account_id = self.env.ref('core.comm')
        self.env.ref('money.get_40000').money_order_done()
        self.receipt.payment = 2.0
        self.receipt.buy_receipt_done()
        self.receipt_return = self.browse_ref('buy.buy_receipt_return_1')
        self.receipt_return.buy_receipt_done()
        self.partner_obj = self.env['buy.summary.partner.wizard']
        self.partner = self.partner_obj.create({})

    def test_button_ok(self):
        '''采购汇总表（按供应商）向导确认按钮'''
        # 日期报错
        partner = self.partner_obj.create({
                             'date_start': '2016-11-01',
                             'date_end': '2016-1-01',
                             })
        with self.assertRaises(except_orm):
            partner.button_ok()

    def test_partner_report(self):
        '''采购汇总表（按供应商）报表'''
        summary_partner = self.env['buy.summary.partner'].create({})
        context = self.partner.button_ok().get('context')
        results = summary_partner.with_context(context).search_read(domain=[])
        new_wizard = self.partner.copy()
        new_wizard.goods_id = self.env.ref('goods.mouse').id
        new_wizard.partner_id = self.env.ref('core.lenovo').id
        new_wizard.s_category_id = \
            self.env.ref('core.supplier_category_1').id
        new_context = new_wizard.button_ok().get('context')
        new_results = summary_partner.with_context(new_context).search_read(
                                                                    domain=[])
        self.assertEqual(len(results), 2)
        self.assertEqual(len(new_results), 0)

    def test_view_detail(self):
        '''采购汇总表（按供应商）  查看明细按钮'''
        summary_partner = self.env['buy.summary.partner'].create({})
        context = self.partner.button_ok().get('context')
        results = summary_partner.with_context(context).search_read(domain=[])
        for line in results:
            summary_line = summary_partner.browse(line['id'])
            summary_line.with_context(context).view_detail()
