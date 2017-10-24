# -*- coding: utf-8 -*-
from odoo.tests.common import TransactionCase
from odoo.exceptions import UserError
import time


class TestQcRule(TransactionCase):
    ''' 测试和仓库相关的商品的有关逻辑 '''

    def setUp(self):
        super(TestQcRule, self).setUp()
        # 入库类型单据
        self.rule_buy = self.env['qc.rule'].create({
            'move_type': 'buy.receipt.buy'})
        self.rule_sell_return = self.env['qc.rule'].create({
            'move_type': 'sell.delivery.return'})
        self.rule_wh_in = self.env['qc.rule'].create({
            'move_type': 'wh.in.others'})
        self.rule_wh_in_inv = self.env['qc.rule'].create({
            'move_type': 'wh.in.inventory'})
        # 出库类型单据
        self.rule_sell = self.env['qc.rule'].create({
            'move_type': 'sell.delivery.sell'})
        self.rule_buy_return = self.env['qc.rule'].create({
            'move_type': 'buy.receipt.return'})
        self.rule_wh_out = self.env['qc.rule'].create({
            'move_type': 'wh.out.others'})
        self.rule_wh_out_inv = self.env['qc.rule'].create({
            'move_type': 'wh.out.inventory'})
        self.warehouse_supplier = self.env.ref('warehouse.warehouse_supplier')
        self.warehouse_customer = self.env.ref('warehouse.warehouse_customer')
        self.warehouse_others = self.env.ref('warehouse.warehouse_others')
        self.warehouse_inventory = self.env.ref(
            'warehouse.warehouse_inventory')

    def test_compute_warehouse_impl(self):
        ''' 根据单据类型自动填充上调出仓库 '''
        self.rule_wh_in.onchange_move_type()
        self.assertTrue(self.rule_wh_in.warehouse_id == self.warehouse_others)
        self.rule_wh_in_inv.onchange_move_type()
        self.assertTrue(self.rule_wh_in_inv.warehouse_id ==
                        self.warehouse_inventory)
        self.rule_buy.onchange_move_type()
        self.assertTrue(self.rule_buy.warehouse_id == self.warehouse_supplier)
        self.rule_sell_return.onchange_move_type()
        self.assertTrue(self.rule_sell_return.warehouse_id ==
                        self.warehouse_customer)

    def test_compute_warehouse_dest_impl(self):
        ''' 根据单据类型自动填充上调入仓库 '''
        self.rule_sell.onchange_move_type()
        self.assertTrue(self.rule_sell.warehouse_dest_id ==
                        self.warehouse_customer)
        self.rule_buy_return.onchange_move_type()
        self.assertTrue(self.rule_buy_return.warehouse_dest_id ==
                        self.warehouse_supplier)
        self.rule_wh_out.onchange_move_type()
        self.assertTrue(self.rule_wh_out.warehouse_dest_id ==
                        self.warehouse_others)
        self.rule_wh_out_inv.onchange_move_type()
        self.assertTrue(self.rule_wh_out_inv.warehouse_dest_id ==
                        self.warehouse_inventory)

    def test_qc_rule_sell_delivery_done(self):
        ''' 满足质检规则但未上传质检报告,应报错:请先上传质检报告 '''
        self.rule_wh_in.onchange_move_type()
        self.rule_wh_in.warehouse_dest_id = self.env.ref('warehouse.hd_stock')
        wh_in_others = self.env.ref('warehouse.wh_in_whin3')
        with self.assertRaises(UserError):
            wh_in_others.approve_order()
