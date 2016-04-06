# -*- coding: utf-8 -*-
from openerp.tests.common import TransactionCase
from openerp.exceptions import except_orm
from datetime import datetime
ISODATEFORMAT = '%Y-%m-%d'
ISODATETIMEFORMAT = "%Y-%m-%d %H:%M:%S"


class test_sell(TransactionCase):

    def test_sell(self):
        ''' 测试销售订单  '''
        # 正常销售订单
        order = self.env.ref('sell.sell_order_1')

        order_2 = self.env.ref('sell.sell_order_2')
        order_3 = self.env.ref('sell.sell_order_3')
        # receipt = self.env['sell.delivery'].search([('order_id', '=', order.id)])

        # 没有订单行的销售订单
        partner_objs = self.env.ref('core.jd')
        vals = {'partner_id': partner_objs.id}
        order_no_line = self.env['sell.order'].create(vals)

        # 计算字段的测试
        self.assertEqual(order.amount, 151600.00)
        # 正常的反审核
        order.sell_order_draft()
        # 正常的  审核销售订单
        # 正常审核后会生成 销售发货单
        order_2.sell_order_done()
        sell_delivery = self.env['sell.delivery'].search([('order_id', '=', order_2.id)])
        sell_delivery.write({"date_due": (datetime.now()).strftime(ISODATEFORMAT)})
        with self.assertRaises(except_orm):
            sell_delivery.sell_delivery_done()
            order_2.unlink()

        with self.assertRaises(except_orm):
            order_2.sell_order_draft()

        # 没有订单行的销售订单
        with self.assertRaises(except_orm):
            order_no_line.sell_order_done()

        for goods_state in [(u'未出库', 0), (u'部分出库', 1), (u'全部出库', 10000)]:
            order.line_ids.write({'quantity_out': goods_state[1]})
            self.assertEqual(order.goods_state, goods_state[0])

        # 销售退货单的测试
        #
        order_3.write({'type': "return"})
        order_3.sell_order_done()

    def test_sale_order_line_compute(self):
        warehouse_id = self.env.ref('warehouse.hd_stock')
        sell_order_line = self.env.ref('sell.sell_order_line_2_3')

        # 测试 产品自动带出 默认值 的仓库
        self.assertEqual(sell_order_line.warehouse_id.id,  warehouse_id.id)

        # sell_order_line 的计算字段的测试
        self.assertEqual(sell_order_line.amount, 90)  # tax_amount subtotal
        self.assertEqual(sell_order_line.tax_rate, 17.0)
        self.assertEqual(sell_order_line.tax_amount, 15.3)
        self.assertEqual(sell_order_line.subtotal, 105.3)

        # onchange test
        print sell_order_line.uom_id
        sell_order_line.goods_id = self.env.ref('goods.mouse')
        # 通过onchange来改变 goods_id
        sell_order_line.onchange_goods_id()

        # 折扣率 on_change 变化
        sell_order_line.discount_rate = 20
        sell_order_line.onchange_discount_rate()
        self.assertEqual(sell_order_line.amount, 80)
