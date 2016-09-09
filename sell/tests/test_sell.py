# -*- coding: utf-8 -*-
from openerp.tests.common import TransactionCase
from openerp.exceptions import except_orm
from datetime import datetime
ISODATEFORMAT = '%Y-%m-%d'
ISODATETIMEFORMAT = "%Y-%m-%d %H:%M:%S"


class Test_sell(TransactionCase):

    def setUp(self):
        super(Test_sell, self).setUp()

        self.env.ref('core.goods_category_1').account_id = self.env.ref('finance.account_goods').id
        self.env.ref('warehouse.wh_in_whin0').date = '2016-02-06'

        self.order = self.env.ref('sell.sell_order_1')

        self.order_2 = self.env.ref('sell.sell_order_2')
        self.order_3 = self.env.ref('sell.sell_order_3')
        self.sell_order_line = self.env.ref('sell.sell_order_line_2_3')
        self.warehouse_dest_id = self.env.ref('warehouse.warehouse_customer')
        self.bank = self.env.ref('core.alipay')
        self.warehouse_id = self.env.ref('warehouse.hd_stock')
        self.customer_warehouse_id = self.env.ref('warehouse.warehouse_customer')
        self.goods = self.env.ref('goods.cable')
        self.partner = self.env.ref('core.lenovo')
        # 因为下面要用到 产品在系统里面必须是有数量的 所以,找到一个简单的方式直接确认已有的盘点单
        warehouse_obj = self.env.ref('warehouse.wh_in_whin0')
        warehouse_obj.approve_order()

        vals = {'partner_id': self.partner.id,
                'is_return': True,
                'date_due': (datetime.now()).strftime(ISODATEFORMAT),
                'warehouse_id': self.customer_warehouse_id.id,
                'warehouse_dest_id': self.warehouse_id.id,
                'line_in_ids': [(0, 0, {'goods_id': self.goods.id,
                                        'price_taxed': 100, 'goods_qty': 5})]}

        self.sell_delivery_obj = self.env['sell.delivery'].with_context({'is_return': True}).create(vals)

        self.order_2.sell_order_done()
        self.sell_delivery = self.env['sell.delivery'].search([('order_id', '=', self.order_2.id)])
        self.sell_delivery.write({"date_due": (datetime.now()).strftime(ISODATEFORMAT)})

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
        self.assertEqual(self.order.amount, 168448.00)
        # 正常的反审核
        self.order.sell_order_draft()

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

        # sell.order onchange test
        self.order.discount_rate = 10
        self.order.onchange_discount_rate()
        self.assertEqual(self.order.discount_amount, 16848.0)

    def test_sale_order_line_compute(self):
        """测试销售订单的on_change 和 计算字段"""

        # sell_order_line 的计算字段的测试
        self.assertEqual(self.sell_order_line.amount, 101.7)  # tax_amount subtotal
        self.assertEqual(self.sell_order_line.tax_rate, 17.0)
        self.assertEqual(self.sell_order_line.tax_amount, 15.3)
        self.assertEqual(self.sell_order_line.subtotal, 117.0)

        # onchange test
        # 折扣率 on_change 变化
        self.sell_order_line.discount_rate = 20
        # 通过onchange来改变 goods_id
        self.sell_order_line.onchange_discount_rate()

        self.assertEqual(self.sell_order_line.amount, 103.4)

    def test_sell_delivery(self):
        """ 销售订单中 on_change 及计算字段"""
        sell_delivery = self.env['sell.delivery'].search([('order_id', '=', self.order_2.id)])
        sell_delivery.discount_rate = 10
        sell_delivery.write({"date_due": (datetime.now()).strftime(ISODATEFORMAT), 'bank_account_id': self.bank.id})
        sell_delivery.onchange_discount_rate()

        self.assertEqual(sell_delivery.money_state, u'未收款')
        self.assertAlmostEqual(sell_delivery.discount_amount, 11.7)
        self.assertEqual(sell_delivery.amount, 105.3)

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
        self.assertEqual(self.sell_delivery_obj.discount_amount, 50)
        #  结算账户 需要输入付款额 测试
        self.sell_delivery_obj.bank_account_id = self.bank.id
        self.sell_delivery_obj.receipt = False
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
        vals = {'partner_id': self.partner.id, 
                'is_return': True, 
                'date_due': (datetime.now()).strftime(ISODATEFORMAT),
                'warehouse_id': self.customer_warehouse_id.id,
                'warehouse_dest_id': self.warehouse_id.id,
                'line_in_ids': [(0, 0, {'goods_id': self.goods.id, 
                                        'price_taxed': 100, 'goods_qty': 5})],
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
        self.assertTrue(order.warehouse_id.type == 'stock')

    def test_onchange_partner_id(self):
        '''选择客户带出其默认地址信息'''
        self.order.onchange_partner_id()

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
        c_category_id = self.order.partner_id.c_category_id
    
        for line in self.order.line_ids:
            line.goods_id = goods
            line.onchange_goods_id()
            self.assertTrue(line.uom_id.name == u'件')
            # 测试价格是否是商品的销售价
            self.assertTrue(line.price_taxed == goods.price)
                
    def test_onchange_warehouse_id(self):
        '''仓库和商品带出价格策略的折扣率'''
        order_line=self.env.ref('sell.sell_order_line_1')
        order_line.onchange_warehouse_id()
        order=self.env.ref('sell.sell_order_1')
        order.partner_id = self.env.ref('core.yixun').id
        order_line.onchange_warehouse_id()

        # 找不到价格策略时
        order.date = False
        order_line.onchange_warehouse_id()
        


class test_sell_delivery(TransactionCase):

    def setUp(self):
        '''准备基本数据'''
        super(test_sell_delivery, self).setUp()

        self.env.ref('core.goods_category_1').account_id = self.env.ref('finance.account_goods').id
        self.env.ref('warehouse.wh_in_whin0').date = '2016-02-06'

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

    def test_onchange_partner_id(self):
        '''选择客户带出其默认地址信息'''
        self.delivery.onchange_partner_id()

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
        '''审核发货单/退货单'''
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

    def test_sell_delivery_draft(self):
        '''反审核发货单/退货单'''
        # 先审核发货单，再反审核
        self.delivery.bank_account_id = self.bank_account.id
        self.delivery.receipt = 5
        for line in self.delivery.line_out_ids:
            line.goods_qty = 8
        self.delivery.sell_delivery_done()
        self.delivery.sell_delivery_draft()
        # 修改发货单，再次审核，并不产生分单
        for line in self.delivery.line_out_ids:
            line.goods_qty = 5
        self.delivery.sell_delivery_done()
        delivery = self.env['sell.delivery'].search(
                       [('order_id', '=', self.order.id)])
        self.assertTrue(len(delivery) == 2)

    def test_no_stock(self):
        ''' 测试虚拟商品出库 '''
        delivery = self.delivery.copy()
        for line in delivery.line_out_ids:
            line.goods_id = self.env.ref('goods.diy')
        delivery.sell_delivery_done()

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

        # 产品的条形码扫码出入库
        barcode = '123456789'
        #销售出库单扫码
        warehouse.scan_barcode(model_name,barcode,delivery_order.id)
        warehouse.scan_barcode(model_name,barcode,delivery_order.id)
        #销售退货扫码
        warehouse.scan_barcode(model_name,barcode,self.return_delivery.id)
        warehouse.scan_barcode(model_name,barcode,self.return_delivery.id)


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
                
    def test_onchange_warehouse_id(self):
        '''wh.move.line仓库和商品带出价格策略的折扣率'''
        for line in self.delivery.line_out_ids[0]:
            line.with_context({'default_date':'2016-04-01',
                               'warehouse_type': 'customer',
                'default_partner': self.delivery.partner_id.id}).onchange_warehouse_id()
            self.assertTrue(line.discount_rate == 10)
            line.with_context({'default_date':'2016-05-01',
                               'warehouse_type': 'customer',
                'default_partner': self.delivery.partner_id.id}).onchange_warehouse_id()
            self.assertTrue(line.discount_rate == 20)
            line.with_context({'default_date':'2016-06-01',
                               'warehouse_type': 'customer',
                'default_partner': self.delivery.partner_id.id}).onchange_warehouse_id()
            self.assertTrue(line.discount_rate == 30)
            line.with_context({'default_date':'2016-07-01',
                               'warehouse_type': 'customer',
                'default_partner': self.delivery.partner_id.id}).onchange_warehouse_id()
            self.assertTrue(line.discount_rate == 40)
            line.with_context({'default_date':'2016-08-01',
                               'warehouse_type': 'customer',
                'default_partner': self.delivery.partner_id.id}).onchange_warehouse_id()
            self.assertTrue(line.discount_rate == 50)
            line.with_context({'default_date':'2016-09-01',
                               'warehouse_type': 'customer',
                'default_partner': self.delivery.partner_id.id}).onchange_warehouse_id()
            self.assertTrue(line.discount_rate == 60)
            line.with_context({'default_date':'2016-10-01',
                               'warehouse_type': 'customer',
                'default_partner': self.delivery.partner_id.id}).onchange_warehouse_id()
            self.assertTrue(line.discount_rate == 70)
            line.with_context({'default_date':'2016-11-01',
                               'warehouse_type': 'customer',
                'default_partner': self.delivery.partner_id.id}).onchange_warehouse_id()
            self.assertTrue(line.discount_rate == 80)
            line.with_context({'default_date':'2016-12-01',
                               'warehouse_type': 'customer',
                'default_partner': self.delivery.partner_id.id}).onchange_warehouse_id()
            self.assertTrue(line.discount_rate == 90)
            line.with_context({'default_date':'3000-02-01',
                               'warehouse_type': 'customer',
                'default_partner': self.delivery.partner_id.id}).onchange_warehouse_id()
            self.assertTrue(line.discount_rate == 0)
            line.with_context({'default_date':'2017-01-01',
                               'warehouse_type': 'customer',
                'default_partner': self.delivery.partner_id.id}).onchange_warehouse_id()
            self.assertTrue(line.discount_rate == 0)

            # 仓库类型不为客户仓时
            line.with_context({'default_date':'2017-01-01',
                'default_partner': self.delivery.partner_id.id}).onchange_warehouse_id()
            self.assertTrue(line.discount_rate == 0)

    def test_onchange_goods_id(self):
        '''测试采购模块中商品的onchange,是否会带出单价'''
        # 销售退货单
        for line in self.delivery_return.line_in_ids:
            line.with_context({'default_is_return': True,
                    'default_partner': self.delivery_return.partner_id.id}).onchange_goods_id()


class test_pricing(TransactionCase):
    
    def test_miss_get_pricing_id(self):
        '''测试定价策略缺少输入的报错问题'''
        warehouse = self.env.ref('warehouse.hd_stock')
        goods = self.env.ref('goods.mouse')
        date = 20160101
        partner = self.env.ref('core.zt')
        pricing = self.env['pricing']
        with self.assertRaises(except_orm):
            pricing.get_pricing_id(False, warehouse, goods, date)
        

        with self.assertRaises(except_orm):
            pricing.get_pricing_id(partner, False, goods, date)

        with self.assertRaises(except_orm):
            pricing.get_pricing_id(partner, warehouse, False, date)

    def test_good_pricing(self):
        '''测试定价输入商品名称、仓库、客户、日期时，定价策略不唯一的情况'''
        pricing = self.env['pricing']
        partner = self.env.ref('core.jd')
        warehouse = self.env.ref('warehouse.bj_stock')
        goods = self.env.ref('goods.mouse')
        date = 20160415
        good_pricing = self.env['pricing'].search([
                                    ('c_category_id', '=', partner.c_category_id.id),
                                    ('warehouse_id', '=', warehouse.id),
                                    ('goods_id', '=', goods.id),
                                    ('goods_category_id', '=', False),
                                    ('active_date', '<=', date),
                                    ('deactive_date', '>=', date)
                                    ])
        cp = good_pricing.copy()
        with self.assertRaises(except_orm):
            pricing.get_pricing_id(partner, warehouse, goods, date)
    
    def test_gc_pricing(self):
        '''测试定价输入商品类别、仓库、客户、日期时，定价策略不唯一的情况'''
        pricing = self.env['pricing']
        partner = self.env.ref('core.jd')
        warehouse = self.env.ref('warehouse.bj_stock')
        goods = self.env.ref('goods.keyboard')
        date = 20160515
        gc_pricing = self.env['pricing'].search([
                                  ('c_category_id','=',partner.c_category_id.id),
                                  ('warehouse_id','=',warehouse.id),
                                  ('goods_id','=',False),
                                  ('goods_category_id','=',goods.category_id.id),
                                  ('active_date','<=',date),
                                  ('deactive_date','>=',date)
                                  ])
        cp = gc_pricing.copy()
        with self.assertRaises(except_orm):
            pricing.get_pricing_id(partner, warehouse, goods, date)

    def test_pw_pricing(self):
        '''测试定价输入仓库、客户、日期时，定价策略不唯一的情况'''
        pricing = self.env['pricing']
        partner = self.env.ref('core.jd')
        warehouse = self.env.ref('warehouse.bj_stock')
        goods = self.env.ref('goods.mouse')
        date = 20160615
        pw_pricing = self.env['pricing'].search([
                                  ('c_category_id','=',partner.c_category_id.id),
                                  ('warehouse_id','=',warehouse.id),
                                  ('goods_id','=',False),
                                  ('goods_category_id','=',False),
                                  ('active_date','<=',date),
                                  ('deactive_date','>=',date)
                                  ])
        cp = pw_pricing.copy()
        with self.assertRaises(except_orm):
            pricing.get_pricing_id(partner, warehouse, goods, date)

    def test_wg_pricing(self):
        '''测试定价输入商品名称、仓库、日期时，定价策略不唯一的情况'''
        pricing = self.env['pricing']
        partner = self.env.ref('core.jd')
        warehouse = self.env.ref('warehouse.bj_stock')
        goods = self.env.ref('goods.mouse')
        date = 20160715
        wg_pricing = self.env['pricing'].search([
                                      ('c_category_id','=',False),
                                      ('warehouse_id','=',warehouse.id),
                                      ('goods_id','=',goods.id),
                                      ('goods_category_id','=',False),
                                      ('active_date','<=',date),
                                      ('deactive_date','>=',date)
                                      ])
        cp = wg_pricing.copy()
        with self.assertRaises(except_orm):
            pricing.get_pricing_id(partner, warehouse, goods, date)
    
    def test_w_gc_pricing(self):
        '''测试定价输入商品类别、仓库、日期时，定价策略不唯一的情况'''
        pricing = self.env['pricing']
        partner = self.env.ref('core.jd')
        warehouse = self.env.ref('warehouse.bj_stock')
        goods = self.env.ref('goods.mouse')
        date = 20160815
        w_gc_pricing = self.env['pricing'].search([
                                      ('c_category_id','=',False),
                                      ('warehouse_id','=',warehouse.id),
                                      ('goods_id','=',False),
                                      ('goods_category_id','=',goods.category_id.id),
                                      ('active_date','<=',date),
                                      ('deactive_date','>=',date)
                                      ])
        cp = w_gc_pricing.copy()
        with self.assertRaises(except_orm):
            pricing.get_pricing_id(partner, warehouse, goods, date)
    
    def test_warehouse_pricing(self):
        '''测试定价输入仓库、日期时，定价策略不唯一的情况'''
        warehouse = self.env.ref('warehouse.bj_stock')
        date = 20160915
        pricing = self.env['pricing']
        partner = self.env.ref('core.jd')
        goods = self.env.ref('goods.mouse')
        warehouse_pricing = self.env['pricing'].search([
                                      ('c_category_id','=',False),
                                      ('warehouse_id','=',warehouse.id),
                                      ('goods_id','=',False),
                                      ('goods_category_id','=',False),
                                      ('active_date','<=',date),
                                      ('deactive_date','>=',date)
                                      ])
        cp = warehouse_pricing.copy()
        with self.assertRaises(except_orm):
            pricing.get_pricing_id(partner, warehouse, goods, date)
    
    def test_ccg_pricing(self):
        '''测试定价输入商品名称、客户、日期时，定价策略不唯一的情况'''
        pricing = self.env['pricing']
        partner = self.env.ref('core.jd')
        goods = self.env.ref('goods.mouse')
        date = 20161015
        warehouse = self.env.ref('warehouse.bj_stock')
        ccg_pricing = self.env['pricing'].search([
                                      ('c_category_id','=',partner.c_category_id.id),
                                      ('warehouse_id','=',False),
                                      ('goods_id','=',goods.id),
                                      ('goods_category_id','=',False),
                                      ('active_date','<=',date),
                                      ('deactive_date','>=',date)
                                      ])
        cp = ccg_pricing.copy()
        with self.assertRaises(except_orm):
            pricing.get_pricing_id(partner, warehouse, goods, date)
    
    def test_ccgc_pricing(self):
        '''测试定价输入商品类别、客户、日期时，定价策略不唯一的情况'''
        pricing = self.env['pricing']
        partner = self.env.ref('core.jd')
        warehouse = self.env.ref('warehouse.bj_stock')
        goods = self.env.ref('goods.mouse')
        date = 20161115
        ccgc_pricing = self.env['pricing'].search([
                                      ('c_category_id','=',partner.c_category_id.id),
                                      ('warehouse_id','=',False),
                                      ('goods_id','=',False),
                                      ('goods_category_id','=',goods.category_id.id),
                                      ('active_date','<=',date),
                                      ('deactive_date','>=',date)
                                      ])
        cp = ccgc_pricing.copy()
        with self.assertRaises(except_orm):
            pricing.get_pricing_id(partner, warehouse, goods, date)

    def test_partner_pricing(self):
        '''测试定价输入客户、日期时，定价策略不唯一的情况'''
        pricing = self.env['pricing']
        partner = self.env.ref('core.jd')
        warehouse = self.env.ref('warehouse.bj_stock')
        goods = self.env.ref('goods.mouse')
        date = 20161215
        partner_pricing = self.env['pricing'].search([
                                      ('c_category_id','=',partner.c_category_id.id),
                                      ('warehouse_id','=',False),
                                      ('goods_id','=',False),
                                      ('goods_category_id','=',False),
                                      ('active_date','<=',date),
                                      ('deactive_date','>=',date)
                                      ])
        cp = partner_pricing.copy()
        with self.assertRaises(except_orm):
            pricing.get_pricing_id(partner, warehouse, goods, date)

    def test_all_goods_pricing(self):
        '''测试定价只输入日期时，定价策略不唯一的情况'''
        pricing = self.env['pricing']
        partner = self.env.ref('core.jd')
        warehouse = self.env.ref('warehouse.bj_stock')
        goods = self.env.ref('goods.mouse')
        date = 20170101
        all_goods_pricing = self.env['pricing'].search([
                                      ('c_category_id','=',False),
                                      ('warehouse_id','=',False),
                                      ('goods_id','=',False),
                                      ('goods_category_id','=',False),
                                      ('active_date','<=',date),
                                      ('deactive_date','>=',date)
                                      ])
        cp = all_goods_pricing.copy()
        with self.assertRaises(except_orm):
            pricing.get_pricing_id(partner, warehouse, goods, date)


class test_sell_adjust(TransactionCase):

    def setUp(self):
        '''销售调整单准备基本数据'''
        super(test_sell_adjust, self).setUp()

        self.env.ref('core.goods_category_1').account_id = self.env.ref('finance.account_goods').id
        self.env.ref('warehouse.wh_in_whin0').date = '2016-02-06'

        # 销货订单 10个 网线
        self.order = self.env.ref('sell.sell_order_2')
        self.order.sell_order_done()
        self.keyboard = self.env.ref('goods.keyboard')
        self.keyboard_white = self.env.ref('goods.keyboard_white')
        self.mouse = self.env.ref('goods.mouse')
        self.cable = self.env.ref('goods.cable')
        # 因为下面要用到 产品在系统里面必须是有数量的 所以,找到一个简单的方式直接确认已有的盘点单
        warehouse_obj = self.env.ref('warehouse.wh_in_whin0')
        warehouse_obj.approve_order()

    def test_unlink(self):
        '''测试删除已审核的销售调整单'''
        adjust = self.env['sell.adjust'].create({
            'order_id': self.order.id,
            'line_ids': [(0, 0, {'goods_id': self.cable.id,
                                 'quantity': 2,
                                }),
                         ]
        })
        adjust.sell_adjust_done()
        with self.assertRaises(except_orm):
            adjust.unlink()
        # 删除草稿状态的销售调整单
        new = adjust.copy()
        new.unlink()

    def test_sell_adjust_done(self):
        '''审核销售调整单:正常情况'''
        # 正常情况下审核，新增产品鼠标（每批次为1的）、键盘（无批次的）
        adjust = self.env['sell.adjust'].create({
            'order_id': self.order.id,
            'line_ids': [(0, 0, {'goods_id': self.cable.id,
                                 'quantity': 2,
                                }),
                         (0, 0, {'goods_id': self.mouse.id,
                                 'quantity': 1,
                                }),
                         (0, 0, {'goods_id': self.keyboard.id,
                                 'attribute_id': self.keyboard_white.id,
                                 'quantity': 1,
                                })
                         ]
        })
        adjust.sell_adjust_done()
        # 重复审核时报错
        with self.assertRaises(except_orm):
            adjust.sell_adjust_done()

    def test_sell_adjust_done_no_line(self):
        '''审核销售调整单:没输入明细行，审核时报错'''
        adjust = self.env['sell.adjust'].create({
            'order_id': self.order.id,
        })
        with self.assertRaises(except_orm):
            adjust.sell_adjust_done()

    def test_sell_adjust_done_all_in(self):
        '''审核销售调整单：销货订单生成的发货单已全部出库，审核时报错'''
        new_order = self.order.copy()
        new_order.sell_order_done()
        delivery = self.env['sell.delivery'].search(
            [('order_id', '=', new_order.id)])
        delivery.discount_amount = 0    # 订单行中价格为0，所以整单金额0
        delivery.sell_delivery_done()
        adjust = self.env['sell.adjust'].create({
            'order_id': new_order.id,
            'line_ids': [(0, 0, {'goods_id': self.cable.id,
                                 'quantity': 1,
                                }),
                         ]
        })
        with self.assertRaises(except_orm):
            adjust.sell_adjust_done()

    def test_sell_adjust_done_more_same_line(self):
        '''审核销售调整单：查找到销货订单中多行同一产品，不能调整'''
        new_order = self.order.copy()
        new_order.line_ids.create({'order_id': new_order.id,
                                   'goods_id': self.cable.id,
                                   'quantity': 10,})
        new_order.sell_order_done()
        delivery = self.env['sell.delivery'].search(
            [('order_id', '=', new_order.id)])
        for line in delivery.line_out_ids:
            line.goods_qty = 1
        delivery.discount_amount = 0    # 订单行中价格为0，所以整单金额0
        delivery.sell_delivery_done()
        adjust = self.env['sell.adjust'].create({
            'order_id': new_order.id,
            'line_ids': [(0, 0, {'goods_id': self.cable.id,
                                 'quantity': 3.0,
                                }),
                         ]
        })
        with self.assertRaises(except_orm):
            adjust.sell_adjust_done()

    def test_sell_adjust_done_quantity_lt(self):
        '''审核销售调整单：调整后数量 5 < 原订单已出库数量 6，审核时报错'''
        delivery = self.env['sell.delivery'].search(
            [('order_id', '=', self.order.id)])
        for line in delivery.line_out_ids:
            line.goods_qty = 6
        delivery.sell_delivery_done()
        adjust = self.env['sell.adjust'].create({
            'order_id': self.order.id,
            'line_ids': [(0, 0, {'goods_id': self.cable.id,
                                'quantity': -5,
                                })]
        })
        with self.assertRaises(except_orm):
            adjust.sell_adjust_done()

    def test_sell_adjust_done_quantity_equal(self):
        '''审核销售调整单:调整后数量6 == 原订单已出库数量 6，审核后将产生的发货单分单删除'''
        delivery = self.env['sell.delivery'].search(
            [('order_id', '=', self.order.id)])
        for line in delivery.line_out_ids:
            line.goods_qty = 6
        delivery.sell_delivery_done()
        adjust = self.env['sell.adjust'].create({
            'order_id': self.order.id,
            'line_ids': [(0, 0, {'goods_id': self.cable.id,
                                'quantity': -4,
                                })]
        })
        adjust.sell_adjust_done()
        new_delivery = self.env['sell.delivery'].search(
            [('order_id', '=', self.order.id),
             ('state', '=', 'draft')])
        self.assertTrue(not new_delivery)

    def test_sell_adjust_done_goods_done(self):
        '''审核销售调整单:原始单据中一行产品已全部出库，另一行没有'''
        new_order = self.order.copy()
        new_order.line_ids.create({'order_id': new_order.id,
                                   'goods_id': self.keyboard.id,
                                   'attribute_id': self.keyboard_white.id,
                                   'quantity': 10})
        new_order.sell_order_done()
        delivery = self.env['sell.delivery'].search(
            [('order_id', '=', new_order.id)])
        for line in delivery.line_out_ids:
            if line.goods_id.id != self.keyboard.id:
                line.unlink()
        delivery.discount_amount = 0    # 订单行中价格为0，所以整单金额0
        delivery.sell_delivery_done()
        adjust = self.env['sell.adjust'].create({
        'order_id': new_order.id,
        'line_ids': [(0, 0, {'goods_id': self.keyboard.id,
                             'attribute_id': self.keyboard_white.id,
                             'quantity': 3.0,
                            }),
                     ]
        })
        with self.assertRaises(except_orm):
            adjust.sell_adjust_done()


class test_sell_adjust_line(TransactionCase):

    def setUp(self):
        '''销售调整单明细基本数据'''
        super(test_sell_adjust_line, self).setUp()
        # 销货订单 10个 网线
        self.order = self.env.ref('sell.sell_order_2')
        self.order.sell_order_done()
        self.keyboard = self.env.ref('goods.keyboard')
        self.cable = self.env.ref('goods.cable')
        self.adjust = self.env['sell.adjust'].create({
            'order_id': self.order.id,
            'line_ids': [(0, 0, {'goods_id': self.cable.id,
                                 'quantity': 1,
                                })]
        })

    def test_compute_using_attribute(self):
        '''返回订单行中产品是否使用属性'''
        for line in self.adjust.line_ids:
            self.assertTrue(not line.using_attribute)
            line.goods_id = self.keyboard
            self.assertTrue(line.using_attribute)

    def test_compute_all_amount(self):
        '''当订单行的数量、单价、折扣额、税率改变时，改变销货金额、税额、价税合计'''
        for line in self.adjust.line_ids:
            line.price_taxed = 117
            self.assertTrue(line.amount == 100)
            self.assertTrue(line.tax_amount == 17)
            self.assertTrue(line.price_taxed == 117)
            self.assertTrue(line.subtotal == 117)

    def test_onchange_goods_id(self):
        '''当销货订单行的产品变化时，带出产品上的单位、价格'''
        for line in self.adjust.line_ids:
            line.goods_id = self.keyboard
            line.onchange_goods_id()
            self.assertTrue(line.uom_id.name == u'件')

    def test_onchange_discount_rate(self):
        ''' 订单行优惠率改变时，改变优惠金额'''
        for line in self.adjust.line_ids:
            line.price_taxed = 117
            line.discount_rate = 10
            line.onchange_discount_rate()
            self.assertTrue(line.discount_amount == 10)
