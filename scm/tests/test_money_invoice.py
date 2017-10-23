# -*- coding: utf-8 -*-
from odoo.tests.common import TransactionCase
from odoo.exceptions import UserError


class TestMoneyInvoice(TransactionCase):

    def setUp(self):
        '''准备基本数据'''
        super(TestMoneyInvoice, self).setUp()
        # 销售相关
        self.order = self.env.ref('sell.sell_order_2')
        self.order.sell_order_done()
        self.delivery = self.env['sell.delivery'].search(
            [('order_id', '=', self.order.id)])
        self.return_order = self.env.ref('sell.sell_order_return')
        self.return_order.sell_order_done()
        self.return_delivery = self.env['sell.delivery'].search(
            [('order_id', '=', self.return_order.id)])

        # 采购相关
        self.order = self.env.ref('buy.buy_order_1')
        self.order.buy_order_done()
        self.receipt = self.env['buy.receipt'].search(
            [('order_id', '=', self.order.id)])
        self.return_receipt = self.env.ref('buy.buy_receipt_return_1')

        # 补足商品，确保审核销售发货单、采购退货单能正常进行
        warehouse_obj = self.env.ref('warehouse.wh_in_whin0')
        warehouse_obj.approve_order()

        # 项目相关
        self.invoice1 = self.env.ref('task.project_invoice_1')

        # 资产相关
        self.asset = self.env.ref('asset.asset_car')
        self.core_jd = self.env.ref('core.jd')

    def test_find_source_order_sell_delivery(self):
        '''结算单上查找原始单据按钮：销售发货、退货单'''
        self.delivery.sell_delivery_done()
        src = self.delivery.invoice_id.find_source_order()
        self.assertEqual(self.delivery.id, src['res_id'])

        self.return_delivery.sell_delivery_done()
        src = self.return_delivery.invoice_id.find_source_order()
        self.assertEqual(self.return_delivery.id, src['res_id'])

    def test_find_source_order_buy_receipt(self):
        '''结算单上查找原始单据按钮：采购入库单、退货单'''
        self.receipt.buy_receipt_done()
        src = self.receipt.invoice_id.find_source_order()
        self.assertEqual(self.receipt.id, src['res_id'])

        self.return_receipt.buy_receipt_done()
        src = self.return_receipt.invoice_id.find_source_order()
        self.assertEqual(self.return_receipt.id, src['res_id'])

    def test_find_source_order_project(self):
        '''结算单上查找原始单据按钮：项目'''
        self.invoice1.project_id.customer_id = self.core_jd
        invoice = self.invoice1.make_invoice()
        src = invoice.find_source_order()
        self.assertEqual(self.invoice1.project_id.id, src['res_id'])

    def test_find_source_order_asset(self):
        '''结算单上查找原始单据按钮：固定资产'''
        self.asset.asset_done()
        src = self.asset.money_invoice.find_source_order()
        self.assertEqual(self.asset.id, src['res_id'])

    def test_find_source_order_asset_change(self):
        '''结算单上查找原始单据按钮：固定资产变更'''
        self.asset.asset_done()
        change_wizard = self.env['create.chang.wizard'].with_context({
            'active_id': self.asset.id}).create({
                'chang_date': '2016-05-01',
                'chang_cost': 200.0,
                'chang_depreciation_number': 1,
                'chang_tax': 34.0,
                'chang_partner_id': self.env.ref('core.zt').id,
            })
        change_wizard.create_chang_account()
        invoice = self.env['money.invoice'].search(
            [('name', '=', u'固定资产变更' + self.asset.code)])
        src = invoice.find_source_order()
        self.assertEqual(self.asset.id, src['res_id'])

    def test_find_source_order_init(self):
        '''结算单上查找原始单据按钮：期初应收'''
        self.core_jd.receivable_init = 1000
        self.core_jd._set_receivable_init()
        invoice = self.env['money.invoice'].search([('name', '=', u'期初应收余额')])
        with self.assertRaises(UserError):
            invoice.find_source_order()
