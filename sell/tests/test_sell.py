# -*- coding: utf-8 -*-
from openerp.tests.common import TransactionCase
from openerp.exceptions import except_orm
from datetime import datetime
ISODATEFORMAT = '%Y-%m-%d'
ISODATETIMEFORMAT = "%Y-%m-%d %H:%M:%S"


class Test_sell(TransactionCase):

    def setUp(self):
        super(Test_sell, self).setUp()
        self.order = self.env.ref('sell.sell_order_1')

        self.order_2 = self.env.ref('sell.sell_order_2')
        self.order_3 = self.env.ref('sell.sell_order_3')
        self.sell_order_line = self.env.ref('sell.sell_order_line_2_3')
        self.warehouse_dest_id = self.env.ref('warehouse.warehouse_customer')
        self.bank = self.env.ref('core.alipay')
        self.warehouse_id = self.env.ref('warehouse.hd_stock')
        self.others_warehouse_id = self.env.ref('warehouse.warehouse_others')
        self.goods = self.env.ref('goods.cable')
        self.goods.default_wh = self.warehouse_id.id
        self.partner = self.env.ref('core.lenovo')
        # 因为下面要用到 产品在系统里面必须是有数量的 所以,找到一个简单的方式直接确认已有的盘点单
        warehouse_obj = self.env.ref('warehouse.wh_in_whin0')
        warehouse_obj.approve_order()

        vals = {'partner_id': self.partner.id, 'is_return': True, 'date_due': (datetime.now()).strftime(ISODATEFORMAT),
                'line_in_ids': [(0, 0, {'goods_id': self.goods.id, 'warehouse_dest_id': self.others_warehouse_id.id,
                                        'price': 100, 'warehouse_id': self.warehouse_id.id, 'goods_qty': 5})]}

        self.sell_delivery_obj = self.env['sell.delivery'].with_context({'is_return': True}).create(vals)

        self.order_2.sell_order_done()
        self.sell_delivery = self.env['sell.delivery'].search([('order_id', '=', self.order_2.id)])
        self.sell_delivery.write({"date_due": (datetime.now()).strftime(ISODATEFORMAT)})
        # 销售退货订单审核，退货出库单审核
        return_receipt = self.env.ref('sell.sell_order_return')
        return_receipt.sell_order_done()
        receipt = self.env['sell.delivery'].search(
                  [('order_id', '=', return_receipt.id)])
        receipt.sell_delivery_done()
    def test_sell(self):
        ''' 测试销售订单  '''
        # 正常销售订单

        # 没有订单行的销售订单
        partner_objs = self.env.ref('core.jd')
        vals = {'partner_id': partner_objs.id}
        order_no_line = self.env['sell.order'].create(vals)
        # 没有订单行的销售订单
        with self.assertRaises(except_orm):
            order_no_line.sell_order_done()

        self.order.sell_order_done()
        # 计算字段的测试
        self.assertEqual(self.order.amount, 151600.00)
        # 正常的反审核
        self.order.sell_order_draft()

        # with self.assertRaises(except_orm):
        #     self.order_2.sell_order_draft()

        for goods_state in [(u'未出库', 0), (u'部分出库', 1), (u'全部出库', 10000)]:
            self.order.line_ids.write({'quantity_out': goods_state[1]})
            self.assertEqual(self.order.goods_state, goods_state[0])
            if goods_state[1] != 0:
                with self.assertRaises(except_orm):
                    self.order.sell_order_done()
                    self.order.sell_order_draft()
            else:
                self.order.sell_order_done()
                self.order.sell_order_draft()

        # # 销售退货单的测试
        # #
        # self.order_3.write({'type': "return"})
        # self.order_3.sell_order_done()

        # sell.order onchange test
        self.order.discount_rate = 10
        self.order.onchange_discount_rate()
        self.assertEqual(self.order.discount_amount, 15163.2)
#         self.order.unlink()

    def test_sale_order_line_compute(self):
        """测试销售订单的on_change 和 计算字段"""
        vals = {
            'order_id': self.order_2.id,
            'goods_id': self.goods.id
        }
        sell_order_line = self.env['sell.order.line']
        sell_order_line._default_warehouse_dest()

        sell_order_line_default = sell_order_line.with_context({'warehouse_dest_type': u'customer'}).create(vals)

        # 测试 产品自动带出 默认值 的仓库
        self.assertEqual(sell_order_line_default.warehouse_dest_id.id,  self.warehouse_dest_id.id)
        # self.assertEqual(sell_order_line_default.warehouse_id.id,  self.warehouse_id.id)

        # sell_order_line 的计算字段的测试
        self.assertEqual(self.sell_order_line.amount, 90)  # tax_amount subtotal
        self.assertEqual(self.sell_order_line.tax_rate, 17.0)
        self.assertEqual(self.sell_order_line.tax_amount, 15.3)
        self.assertEqual(self.sell_order_line.subtotal, 105.3)

        # onchange test
        self.sell_order_line.goods_id = self.env.ref('goods.mouse')
        # 折扣率 on_change 变化
        self.sell_order_line.discount_rate = 20
        # 通过onchange来改变 goods_id
#         self.sell_order_line.onchange_goods_id()
        self.sell_order_line.onchange_discount_rate()

        self.assertEqual(self.sell_order_line.amount, 80)

    def test_sell_delivery(self):
        """ 销售订单中 on_change 及计算字段"""
        sell_delivery = self.env['sell.delivery'].search([('order_id', '=', self.order_2.id)])
        sell_delivery.discount_rate = 10
        sell_delivery.write({"date_due": (datetime.now()).strftime(ISODATEFORMAT), 'bank_account_id': self.bank.id})
        sell_delivery.onchange_discount_rate()

        self.assertEqual(sell_delivery.money_state, u'未收款')
        self.assertEqual(sell_delivery.discount_amount, 10.53)
        self.assertEqual(sell_delivery.amount, 94.77)

        # 销售发货单 的确认
        sell_delivery.receipt = 22
        sell_delivery.sell_delivery_done()

        self.assertEqual(sell_delivery.money_state, u'部分收款')

    def test_sell_delievery_in(self):
        """ 销售 退货单 的付款状态的测试"""
        for sell_delivery_line_obj in self.sell_delivery_obj.line_in_ids:
            sell_delivery_line_obj.discount_rate = 10
            sell_delivery_line_obj.onchange_discount_rate()
            self.assertEqual(sell_delivery_line_obj.discount_amount, 50)
        # 退货单折扣率测试
        self.sell_delivery_obj.discount_rate = 10
        self.sell_delivery_obj.onchange_discount_rate()
        self.assertEqual(self.sell_delivery_obj.discount_amount, 52.65)
        #  结算账户 需要输入付款额 测试
        self.sell_delivery_obj.bank_account_id = self.bank.id
        self.receipt = False
        with self.assertRaises(except_orm):
            self.sell_delivery_obj.sell_delivery_done()

    def test_no_account_id(self):
        """销售发货单付款账户审核时为空 测试"""
        self.sell_delivery.bank_account_id = False
        self.sell_delivery.receipt = 20
        with self.assertRaises(except_orm):
            self.sell_delivery.sell_delivery_done()

    def test_sale_usage_return(self):
        """测试销售退货单 审核流程"""
        vals = {'partner_id': self.partner.id, 'is_return': True, 'date_due': (datetime.now()).strftime(ISODATEFORMAT),
                'line_in_ids': [(0, 0, {'goods_id': self.goods.id, 'warehouse_dest_id': self.others_warehouse_id.id,
                                        'price': 100, 'warehouse_id': self.warehouse_id.id, 'goods_qty': 5})],
                'cost_line_ids': [(0, 0, {'partner_id': self.partner.id,
                                          'category_id': self.env.ref('core.cat_freight').id,
                                          'amount': 50})]}

        sell_delivery_obj = self.env['sell.delivery'].create(vals)
        sell_delivery_obj.sell_delivery_done()

    def test_account_id_receipt(self):
        ''' 发货单 本次收款金额 大于总金额  '''
        self.sell_delivery.receipt = 100000
        self.sell_delivery.amount = 10
        self.sell_delivery.bank_account_id = self.bank.id
        with self.assertRaises(except_orm):
            self.sell_delivery.sell_delivery_done()


class test_sell_order(TransactionCase):

    def setUp(self):
        super(test_sell_order, self).setUp()
        self.order = self.env.ref('sell.sell_order_1')

    def test_default_warehouse(self):
        '''新建销货订单时调出仓库的默认值'''
        order = self.env['sell.order'].with_context({
             'warehouse_type': 'stock'
             }).create({})
        # 验证明细行上仓库是否是销货订单上调出仓库
        hd_stock = self.browse_ref('warehouse.hd_stock')
        order.warehouse_id = hd_stock
        line = order.line_ids.with_context({
            'default_warehouse_id': order.warehouse_id}).create({
            'order_id': order.id})
        self.assertTrue(line.warehouse_id == hd_stock)
        self.env['sell.order'].create({})

    def test_unlink(self):
        '''测试删除已审核的销货订单'''
        self.order.sell_order_done()
        with self.assertRaises(except_orm):
            self.order.unlink()
        # 删除草稿状态的销货订单
        self.order.copy()
        self.order.sell_order_draft()
        self.order.unlink()

    def test_sell_order_done(self):
        '''测试审核销货订单'''
        # 审核销货订单
        self.order.sell_order_done()
        with self.assertRaises(except_orm):
            self.order.sell_order_done()

        # 未填数量应报错
        self.order.sell_order_draft()
        for line in self.order.line_ids:
            line.quantity = 0
        with self.assertRaises(except_orm):
            self.order.sell_order_done()

        # 输入预收款和结算账户
        bank_account = self.env.ref('core.alipay')
        bank_account.balance = 1000000
        self.order.pre_receipt = 50.0
        self.order.bank_account_id = bank_account
        for line in self.order.line_ids:
            line.quantity = 1
        self.order.sell_order_done()

        # 预收款不为空时，请选择结算账户！
        self.order.sell_order_draft()
        self.order.bank_account_id = False
        self.order.pre_receipt = 50.0
        with self.assertRaises(except_orm):
            self.order.sell_order_done()
        # 结算账户不为空时，需要输入预收款！
        self.order.bank_account_id = bank_account
        self.order.pre_receipt = 0
        with self.assertRaises(except_orm):
            self.order.sell_order_done()

        # 没有订单行时审核报错
        for line in self.order.line_ids:
            line.unlink()
        with self.assertRaises(except_orm):
            self.order.sell_order_done()

    def test_sell_order_draft(self):
        ''' 测试反审核销货订单  '''
        self.order.sell_order_done()
        self.order.sell_order_draft()
        with self.assertRaises(except_orm):
            self.order.sell_order_draft()


class test_sell_order_line(TransactionCase):

    def setUp(self):
        super(test_sell_order_line, self).setUp()
        self.order = self.env.ref('sell.sell_order_1')

    def test_compute_using_attribute(self):
        '''返回订单行中产品是否使用属性'''
        for line in self.order.line_ids:
            self.assertTrue(not line.using_attribute)
            line.goods_id = self.env.ref('goods.keyboard')
            self.assertTrue(line.using_attribute)

    def test_onchange_goods_id(self):
        '''当销货订单行的产品变化时，带出产品上的单位、价格'''
        goods = self.env.ref('goods.keyboard')
        goods.default_wh = self.env.ref('warehouse.hd_stock').id
        c_category_id = self.order.partner_id.c_category_id
        price_ids = self.env['goods.price'].search(
                                [('goods_id', '=', goods.id),
                                 ('category_id', '=', c_category_id.id)])
        for line in self.order.line_ids:
            line.goods_id = goods
            line.onchange_goods_id()
            self.assertTrue(line.uom_id.name == u'件')

            # 测试价格是否是商品价格清单中的价格
            self.assertTrue(line.price == price_ids.price)
            # 测试不设置订单客户的客户类别时是否弹出警告
            self.order.partner_id.c_category_id = False
            with self.assertRaises(except_orm):
                line.onchange_goods_id()


class test_sell_delivery(TransactionCase):

    def setUp(self):
        '''准备基本数据'''
        super(test_sell_delivery, self).setUp()
        self.order = self.env.ref('sell.sell_order_2')
        self.order.sell_order_done()
        self.delivery = self.env['sell.delivery'].search(
                       [('order_id', '=', self.order.id)])
        self.return_order = self.env.ref('sell.sell_order_return')
        self.return_order.sell_order_done()
        self.return_delivery = self.env['sell.delivery'].search(
                       [('order_id', '=', self.return_order.id)])
        warehouse_obj = self.env.ref('warehouse.wh_in_whin0')
        warehouse_obj.approve_order()

        self.bank_account = self.env.ref('core.alipay')
        self.bank_account.balance = 10000

    def test_get_sell_money_state(self):
        '''测试返回收款状态'''
        # 未收款
        self.delivery.sell_delivery_done()
        self.delivery._get_sell_money_state()
        self.assertEqual(self.delivery.money_state, u'未收款')

        # 部分收款
        delivery = self.delivery.copy()
        delivery.receipt = delivery.amount - 1
        delivery.bank_account_id = self.bank_account
        delivery.sell_delivery_done()
        delivery._get_sell_money_state()
        self.assertEqual(delivery.money_state, u'部分收款')

        # 全部收款
        delivery = self.delivery.copy()
        delivery.receipt = delivery.amount
        delivery.bank_account_id = self.bank_account
        delivery.sell_delivery_done()
        delivery._get_sell_money_state()
        self.assertEqual(delivery.money_state, u'全部收款')

    def test_get_sell_return_state(self):
        '''测试返回退款状态'''
        #  未退款
        self.return_delivery.sell_delivery_done()
        self.return_delivery._get_sell_return_state()
        self.assertEqual(self.return_delivery.return_state, u'未退款')

        #  部分退款
        return_delivery = self.return_delivery.copy()
        return_delivery.receipt = return_delivery.amount - 1
        return_delivery.bank_account_id = self.bank_account
        return_delivery.sell_delivery_done()
        return_delivery._get_sell_return_state()
        self.assertEqual(return_delivery.return_state, u'部分退款')

        #  全部退款
        return_delivery = self.return_delivery.copy()
        return_delivery.receipt = return_delivery.amount
        return_delivery.bank_account_id = self.bank_account
        return_delivery.sell_delivery_done()
        return_delivery._get_sell_return_state()
        self.assertEqual(return_delivery.return_state, u'全部退款')

    def test_unlink(self):
        '''测试删除销售发货/退货单'''
        # 测试是否可以删除已审核的单据
        self.delivery.sell_delivery_done()
        with self.assertRaises(except_orm):
            self.delivery.unlink()

        # 删除销售发货单时，测试能否删除发货单行
        delivery = self.delivery.copy()
        move_id = delivery.sell_move_id.id
        delivery.unlink()
        move = self.env['wh.move'].search(
               [('id', '=', move_id)])
        self.assertTrue(not move)
        self.assertTrue(not move.line_out_ids)

    def test_sell_delivery_done(self):
        '''测试审核发货单/退货单'''
        # 销售发货单重复审核
        delivery = self.delivery.copy()
        delivery.sell_delivery_done()
        with self.assertRaises(except_orm):
            delivery.sell_delivery_done()
        # 发货单审核时未填数量应报错
        for line in self.delivery.line_out_ids:
            line.goods_qty = 0
        with self.assertRaises(except_orm):
            self.delivery.sell_delivery_done()
        # 销售退货单审核时未填数量应报错
        for line in self.return_delivery.line_in_ids:
            line.goods_qty = 0
        with self.assertRaises(except_orm):
            self.return_delivery.sell_delivery_done()

    def test_scan_barcode(self):
        '''销售扫码出入库'''
        warehouse = self.env['wh.move']
        barcode = '12345678987'
        #销售退货扫码
        model_name = 'sell.delivery'
        warehouse.scan_barcode(model_name,barcode,self.return_delivery.id)
        warehouse.scan_barcode(model_name,barcode,self.return_delivery.id)
        #销售出库单扫码
        sell_order = self.env.ref('sell.sell_order_1')
        sell_order.sell_order_done()
        delivery_order = self.env['sell.delivery'].search([('order_id', '=', sell_order.id)])
        warehouse.scan_barcode(model_name,barcode,delivery_order.id)
        warehouse.scan_barcode(model_name,barcode,delivery_order.id)


class test_wh_move_line(TransactionCase):

    def setUp(self):
        '''准备基本数据'''
        super(test_wh_move_line, self).setUp()
        self.sell_return = self.browse_ref('sell.sell_order_return')
        self.sell_return.sell_order_done()
        self.delivery_return = self.env['sell.delivery'].search(
                  [('order_id', '=', self.sell_return.id)])

        self.sell_order = self.env.ref('sell.sell_order_1')
        self.sell_order.sell_order_done()
        self.delivery = self.env['sell.delivery'].search(
                        [('order_id', '=', self.sell_order.id)])

        self.goods_cable = self.browse_ref('goods.cable')
        self.goods_keyboard = self.browse_ref('goods.keyboard')

    def test_onchange_goods_id(self):
        '''测试销售模块中商品的onchange,是否会带出默认库位和单价'''
        # 销售退货单行
        for line in self.delivery_return.line_in_ids:
            # 在商品鼠标的价格清单中没有找到匹配的价格
            with self.assertRaises(except_orm):
                line.with_context({'default_is_return': True,
                    'default_partner': self.delivery_return.partner_id.id}).onchange_goods_id()
            # 在商品键盘的价格清单中找到匹配的价格
            line.goods_id = self.goods_keyboard.id
            line.with_context({'default_is_return': True,
                'default_partner': self.delivery_return.partner_id.id}).onchange_goods_id()

        # 发货单行：
        for line in self.delivery.line_out_ids:
            line.goods_id = self.goods_keyboard.id
            line.with_context({'default_is_return': False,
                'default_partner': self.delivery.partner_id.id}).onchange_goods_id()
            line.goods_id = self.goods_cable.id
            with self.assertRaises(except_orm):
                line.with_context({'default_is_return': False,
                'default_partner': self.delivery.partner_id.id}).onchange_goods_id()
