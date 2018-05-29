# -*- coding: utf-8 -*-
from odoo.tests.common import TransactionCase
from odoo.exceptions import UserError


class TestSellDeliveryByParts(TransactionCase):
    def setUp(self):
        ''' setUp Data '''
        super(TestSellDeliveryByParts, self).setUp()
        self.partner = self.env.ref('core.jd')
        self.warehouse_id = self.env.ref('warehouse.hd_stock')
        self.customer_warehouse_id = self.env.ref('warehouse.warehouse_customer')
        self.keyboard_mouse = self.env.ref('goods.keyboard_mouse')  # goods  mouse
        self.keyboard_mouse.is_assembly_sell = True

    def test_create_goods_assembly_sell(self):
        ''' Test create method: goods assembly sell '''
        delivery = self.env['sell.delivery'].create({
                                            'partner_id': self.partner.id,
                                            'warehouse_id': self.warehouse_id.id,
                                            'warehouse_dest_id': self.customer_warehouse_id.id
                                            })
        out_line_vals = {'goods_id': self.keyboard_mouse.id,
                        'price_taxed': 100,
                        'goods_qty': 1,
                        'type': 'out'}
        # 报错：找不到物料清单
        with self.assertRaises(UserError):
            delivery.line_out_ids.create(out_line_vals)

        self.assembly = self.env.ref('warehouse.wh_bom_0')
        self.assembly.type = 'assembly'
        delivery.line_out_ids.create(out_line_vals)

        # 商品部件存在零售价格
        self.env.ref('goods.mouse').price = 100
        self.env.ref('goods.keyboard').price = 300
        delivery.line_out_ids.create(out_line_vals)
