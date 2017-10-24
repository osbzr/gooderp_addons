# -*- coding: utf-8 -*-
from odoo.tests.common import TransactionCase
from odoo.exceptions import UserError
from datetime import datetime
ISODATEFORMAT = '%Y-%m-%d'


class TestSellDelivery(TransactionCase):

    def setUp(self):
        '''准备基本数据'''
        super(TestSellDelivery, self).setUp()
        self.env.ref('core.jd').credit_limit = 100000
        self.env.ref('core.goods_category_1').account_id = self.env.ref(
            'finance.account_goods').id
        self.env.ref('warehouse.wh_in_whin0').date = '2016-02-06'

        # 因同一个业务伙伴不能存在两张未审核的收付款单，把系统里已有的相关业务伙伴未审核的收付款单审核
        self.env.ref('money.get_40000').money_order_done()
        self.env.ref('money.pay_2000').money_order_done()

        self.bank_account = self.env.ref('core.alipay')
        self.bank_account.balance = 10000

        self.order = self.env.ref('sell.sell_order_2')
        self.order.bank_account_id = self.bank_account.id
        self.order.pre_receipt = 1
        self.order.sell_order_done()
        self.delivery = self.env['sell.delivery'].search(
            [('order_id', '=', self.order.id)])
        self.return_order = self.env.ref('sell.sell_order_return')
        self.return_order.sell_order_done()
        self.return_delivery = self.env['sell.delivery'].search(
            [('order_id', '=', self.return_order.id)])
        warehouse_obj = self.env.ref('warehouse.wh_in_whin0')
        warehouse_obj.approve_order()

        self.warehouse_id = self.env.ref('warehouse.hd_stock')
        self.customer_warehouse_id = self.env.ref(
            'warehouse.warehouse_customer')
        self.goods = self.env.ref('goods.cable')
        self.partner = self.env.ref('core.lenovo')

        self.province_id = self.env['country.state'].search(
            [('name', '=', u'河北省')])
        self.city_id = self.env['all.city'].search(
            [('city_name', '=', u'石家庄市')])
        self.county_id = self.env['all.county'].search(
            [('county_name', '=', u'正定县')])

    def test_onchange_partner_id(self):
        '''选择客户带出其默认地址信息'''
        # partner 不存在默认联系人
        partner = self.env.ref('core.jd')
        partner.write({'child_ids':
                       [(0, 0, {'contact': u'小东',
                                'province_id': self.province_id.id,
                                'city_id': self.city_id.id,
                                'county_id': self.county_id.id,
                                'town': u'曹路镇',
                                'detail_address': u'金海路1688号',
                                }
                         )]})
        self.delivery.onchange_partner_id()
        # partner 存在默认联系人
        for child in partner.child_ids:
            child.mobile = '1385559999'
            child.phone = '55558888'
            child.qq = '11116666'
            child.is_default_add = True
        self.delivery.onchange_partner_id()

    def test_onchange_address(self):
        ''' sell.delivery onchange address '''
        address = self.env['partner.address'].create({'contact': u'小东',
                                                      'province_id': self.province_id.id,
                                                      'city_id': self.city_id.id,
                                                      'county_id': self.county_id.id,
                                                      'town': u'曹路镇',
                                                      'detail_address': u'金海路1688号',
                                                      })
        self.delivery.address_id = address.id
        self.delivery.onchange_address_id()

    def test_onchange_discount_rate(self):
        """ 发货单中折扣率 on_change"""
        self.delivery.discount_rate = 10
        self.delivery.write(
            {"date_due": (datetime.now()).strftime(ISODATEFORMAT)})
        self.delivery.onchange_discount_rate()
        self.assertAlmostEqual(self.delivery.discount_amount, 10.70)

    def test_onchange_discount_rate_in(self):
        """ 销售 退货单 的折扣率 on_change 测试"""
        self.return_delivery.discount_rate = 10
        self.return_delivery.onchange_discount_rate()
        self.assertAlmostEqual(self.return_delivery.discount_amount, 10.70)

    def test_get_sell_money_state(self):
        '''测试返回收款状态'''
        # 未收款
        self.delivery.sell_delivery_done()
        self.delivery.sell_to_return()
        self.delivery._get_sell_money_state()
        self.assertEqual(self.delivery.money_state, u'未收款')

        # 部分收款
        delivery = self.delivery.copy()
        delivery.receipt = delivery.amount - 1
        delivery.bank_account_id = self.bank_account
        delivery.sell_delivery_done()

        # 判断状态
        delivery._get_sell_money_state()
        self.assertEqual(delivery.money_state, u'部分收款')

        # 全部收款
        delivery = self.delivery.copy()
        delivery.receipt = delivery.amount
        delivery.bank_account_id = self.bank_account
        delivery.sell_delivery_done()

        # 判断状态
        delivery._get_sell_money_state()
        self.assertEqual(delivery.money_state, u'全部收款')

    def test_get_sell_money_state_return(self):
        '''测试返回退款状态'''
        #  未退款
        self.return_delivery.sell_delivery_done()
        self.return_delivery._get_sell_money_state()
        self.assertEqual(self.return_delivery.return_state, u'未退款')

        #  部分退款
        return_delivery = self.return_delivery.copy()
        return_delivery.receipt = return_delivery.amount - 1
        return_delivery.bank_account_id = self.bank_account
        return_delivery.sell_delivery_done()

        # 判断状态
        return_delivery._get_sell_money_state()
        self.assertEqual(return_delivery.return_state, u'部分退款')

        #  全部退款
        return_delivery = self.return_delivery.copy()
        return_delivery.receipt = return_delivery.amount
        return_delivery.bank_account_id = self.bank_account
        return_delivery.sell_delivery_done()
        # 判断状态
        return_delivery._get_sell_money_state()
        self.assertEqual(return_delivery.return_state, u'全部退款')

    def test_unlink(self):
        '''测试删除销售发货/退货单'''
        # 测试是否可以删除已审核的单据
        self.delivery.sell_delivery_done()
        with self.assertRaises(UserError):
            self.delivery.unlink()

        # 删除销售发货单时，测试能否删除发货单行
        delivery = self.delivery.copy()
        move_id = delivery.sell_move_id.id
        delivery.unlink()
        move = self.env['wh.move'].search(
            [('id', '=', move_id)])
        self.assertTrue(not move)
        self.assertTrue(not move.line_out_ids)

    def test_sell_delievery_done_no_account_id(self):
        """销售 发货单 审核时付款账户为空 测试"""
        self.delivery.bank_account_id = False
        self.delivery.receipt = 20
        with self.assertRaises(UserError):
            self.delivery.sell_delivery_done()

    def test_sell_delievery_done_receipt_greater_than_amount(self):
        ''' 发货单 本次收款金额 大于总金额  '''
        self.delivery.receipt = 100000
        self.delivery.amount = 10
        self.delivery.bank_account_id = self.bank_account.id
        with self.assertRaises(UserError):
            self.delivery.sell_delivery_done()

    def test_sell_delivery_done_wrong(self):
        '''审核发货单/退货单报错情况'''
        # 销售发货单重复审核
        delivery = self.delivery
        delivery.sell_delivery_done()
        with self.assertRaises(UserError):
            delivery.sell_delivery_done()
        # 发货单审核时未填数量应报错
        for line in self.delivery.line_out_ids:
            line.goods_qty = 0
        with self.assertRaises(UserError):
            self.delivery.sell_delivery_done()
        # 销售退货单审核时未填数量应报错
        for line in self.return_delivery.line_in_ids:
            line.goods_qty = 0
        with self.assertRaises(UserError):
            self.return_delivery.sell_delivery_done()

    def test_auto_reconcile_sell_order(self):
        ''' 预收款与结算单自动核销 '''
        delivery = self.delivery
        delivery.receipt = 74
        delivery.bank_account_id = self.bank_account
        delivery.sell_delivery_done()

    def test_sell_delivery_done(self):
        """审核退货单正常流程"""
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

        return_delivery = self.env['sell.delivery'].create(vals)
        return_delivery.sell_delivery_done()

    def test_sell_delivery_done_goods_inventory(self):
        '''发库单审核时商品不足直接盘盈'''
        for line in self.delivery.line_out_ids:
            line.goods_id = self.env.ref('goods.computer')
        self.delivery.sell_delivery_done()

    def test_goods_inventory(self):
        '''发库单审核商品不足时调用创建盘盈入库方法'''
        for line in self.delivery.line_out_ids:
            vals = {
                'type': 'inventory',
                'warehouse_id': self.env.ref('warehouse.warehouse_inventory').id,
                'warehouse_dest_id': self.delivery.warehouse_id.id,
                'line_in_ids': [(0, 0, {
                        'goods_id': line.goods_id.id,
                        'attribute_id': line.attribute_id.id,
                        'uos_id': line.uos_id.id,
                        'goods_qty': line.goods_qty,
                                'uom_id': line.uom_id.id,
                                'cost_unit': line.goods_id.cost
                                }
                )]
            }
            self.delivery.goods_inventory(vals)
            # no message
            self.delivery.open_dialog('goods_inventory', vals)

    def test_sell_delivery_done_raise_credit_limit(self):
        '''审核发货单/退货单 客户的 本次发货金额+客户应收余额 不能大于客户信用额度'''
        self.delivery.amount = 20000000
        with self.assertRaises(UserError):
            self.delivery.sell_delivery_done()

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
        # 销售退货扫码
        model_name = 'sell.delivery'
        warehouse.scan_barcode(model_name, barcode, self.return_delivery.id)
        warehouse.scan_barcode(model_name, barcode, self.return_delivery.id)
        # 销售出库单扫码
        sell_order = self.env.ref('sell.sell_order_1')
        self.env.ref('sell.sell_order_line_1').tax_rate = 0
        sell_order.sell_order_done()
        delivery_order = self.env['sell.delivery'].search(
            [('order_id', '=', sell_order.id)])
        warehouse.scan_barcode(model_name, barcode, delivery_order.id)
        warehouse.scan_barcode(model_name, barcode, delivery_order.id)

        # 商品的条形码扫码出入库
        barcode = '123456789'
        # 销售出库单扫码
        warehouse.scan_barcode(model_name, barcode, delivery_order.id)
        warehouse.scan_barcode(model_name, barcode, delivery_order.id)
        # 销售退货扫码
        warehouse.scan_barcode(model_name, barcode, self.return_delivery.id)
        warehouse.scan_barcode(model_name, barcode, self.return_delivery.id)

    def test_onchange_partner_id_tax_rate(self):
        ''' 测试 改变 partner, 出库单行商品税率变化 '''
        delivery = self.env['sell.delivery'].search(
            [('order_id', '=', self.order.id)])
        # partner 无 税率， 出库单行商品无税率
        self.env.ref('core.jd').tax_rate = 0
        self.env.ref('goods.cable').tax_rate = 0
        delivery.onchange_partner_id()
        # partner 有 税率， 出库单行商品无税率
        self.env.ref('core.jd').tax_rate = 10
        self.env.ref('goods.cable').tax_rate = 0
        delivery.onchange_partner_id()
        # partner 无税率， 出库单行商品无税率
        self.env.ref('core.jd').tax_rate = 0
        self.env.ref('goods.cable').tax_rate = 10
        delivery.onchange_partner_id()
        # partner 税率 >  出库单行商品税率
        self.env.ref('core.jd').tax_rate = 11
        self.env.ref('goods.cable').tax_rate = 10
        delivery.onchange_partner_id()
        # partner 税率 =<  出库单行商品税率
        self.env.ref('core.jd').tax_rate = 11
        self.env.ref('goods.cable').tax_rate = 12
        delivery.onchange_partner_id()

    def test_sell_delivery_done_currency(self):
        """发货单上是外币时进行审核"""
        self.delivery.currency_id = self.env.ref('base.USD')
        self.delivery.sell_delivery_done()


class TestWhMoveLine(TransactionCase):

    def setUp(self):
        '''准备基本数据'''
        super(TestWhMoveLine, self).setUp()
        self.env.ref('core.jd').credit_limit = 100000
        self.sell_return = self.browse_ref('sell.sell_order_return')
        self.sell_return.sell_order_done()
        self.delivery_return = self.env['sell.delivery'].search(
            [('order_id', '=', self.sell_return.id)])

        self.sell_order = self.env.ref('sell.sell_order_1')
        self.env.ref('sell.sell_order_line_1').tax_rate = 0
        self.sell_order.sell_order_done()
        self.delivery = self.env['sell.delivery'].search(
            [('order_id', '=', self.sell_order.id)])

        self.goods_cable = self.browse_ref('goods.cable')
        self.goods_keyboard = self.browse_ref('goods.keyboard')
        self.warehouse_id = self.env.ref('warehouse.hd_stock')
        self.customer_warehouse_id = self.env.ref(
            'warehouse.warehouse_customer')
        self.partner = self.env.ref('core.jd')

        vals = {'partner_id': self.partner.id,
                'is_return': False,
                'date_due': (datetime.now()).strftime(ISODATEFORMAT),
                'warehouse_id': self.customer_warehouse_id.id,
                'warehouse_dest_id': self.warehouse_id.id,
                'line_out_ids': [(0, 0, {'goods_id': self.goods_cable.id,
                                         'goods_qty': 5,
                                         'tax_rate': 17.0,
                                         'type': 'out'})],
                }
        self.new_delivery = self.env['sell.delivery'].create(vals)

    def test_onchange_warehouse_id(self):
        '''wh.move.line仓库和商品带出价格策略的折扣率'''
        for line in self.delivery.line_out_ids[0]:
            line.with_context({'default_date': '2016-04-01',
                               'warehouse_type': 'customer',
                               'default_partner': self.delivery.partner_id.id}).onchange_warehouse_id()
            self.assertTrue(line.discount_rate == 10)
            line.with_context({'default_date': '2016-05-01',
                               'warehouse_type': 'customer',
                               'default_partner': self.delivery.partner_id.id}).onchange_warehouse_id()
            self.assertTrue(line.discount_rate == 20)
            line.with_context({'default_date': '2016-06-01',
                               'warehouse_type': 'customer',
                               'default_partner': self.delivery.partner_id.id}).onchange_warehouse_id()
            self.assertTrue(line.discount_rate == 30)
            line.with_context({'default_date': '2016-07-01',
                               'warehouse_type': 'customer',
                               'default_partner': self.delivery.partner_id.id}).onchange_warehouse_id()
            self.assertTrue(line.discount_rate == 40)
            line.with_context({'default_date': '2016-08-01',
                               'warehouse_type': 'customer',
                               'default_partner': self.delivery.partner_id.id}).onchange_warehouse_id()
            self.assertTrue(line.discount_rate == 50)
            line.with_context({'default_date': '2016-09-01',
                               'warehouse_type': 'customer',
                               'default_partner': self.delivery.partner_id.id}).onchange_warehouse_id()
            self.assertTrue(line.discount_rate == 60)
            line.with_context({'default_date': '2016-10-01',
                               'warehouse_type': 'customer',
                               'default_partner': self.delivery.partner_id.id}).onchange_warehouse_id()
            self.assertTrue(line.discount_rate == 70)
            line.with_context({'default_date': '2016-11-01',
                               'warehouse_type': 'customer',
                               'default_partner': self.delivery.partner_id.id}).onchange_warehouse_id()
            self.assertTrue(line.discount_rate == 80)
            line.with_context({'default_date': '2016-12-01',
                               'warehouse_type': 'customer',
                               'default_partner': self.delivery.partner_id.id}).onchange_warehouse_id()
            self.assertTrue(line.discount_rate == 90)
            line.with_context({'default_date': '3000-02-01',
                               'warehouse_type': 'customer',
                               'default_partner': self.delivery.partner_id.id}).onchange_warehouse_id()
            self.assertTrue(line.discount_rate == 0)
            line.with_context({'default_date': '2017-01-01',
                               'warehouse_type': 'customer',
                               'default_partner': self.delivery.partner_id.id}).onchange_warehouse_id()
            self.assertTrue(line.discount_rate == 0)

            # 仓库类型不为客户仓时
            line.with_context({'default_date': '2017-01-01',
                               'default_partner': self.delivery.partner_id.id}).onchange_warehouse_id()
            self.assertTrue(line.discount_rate == 0)

    def test_onchange_goods_id(self):
        '''测试销售模块中商品的onchange,是否会带出单价'''
        # 销售退货单
        for line in self.delivery_return.line_in_ids:
            line.with_context({'default_is_return': True,
                               'default_partner': self.delivery_return.partner_id.id}).onchange_goods_id()

    def test_onchange_goods_id_tax_rate(self):
        ''' 测试 修改商品时，出库单行税率变化 '''
        for order_line in self.delivery.line_out_ids:
            # partner 无 税率，出库单行商品无税率
            self.partner.tax_rate = 0
            self.env.ref('goods.mouse').tax_rate = 0
            order_line.with_context(
                {'default_partner': self.delivery.partner_id.id}).onchange_goods_id()
            # partner 有 税率，出库单行商品无税率
            self.partner.tax_rate = 10
            self.env.ref('goods.mouse').tax_rate = 0
            order_line.with_context(
                {'default_partner': self.delivery.partner_id.id}).onchange_goods_id()
            # partner 无税率，出库单行商品有税率
            self.partner.tax_rate = 0
            self.env.ref('goods.mouse').tax_rate = 10
            order_line.with_context(
                {'default_partner': self.delivery.partner_id.id}).onchange_goods_id()
            # partner 税率 > 出库单行商品税率
            self.partner.tax_rate = 11
            self.env.ref('goods.mouse').tax_rate = 10
            order_line.with_context(
                {'default_partner': self.delivery.partner_id.id}).onchange_goods_id()
            # partner 税率 =< 出库单行商品税率
            self.partner.tax_rate = 9
            self.env.ref('goods.mouse').tax_rate = 10
            order_line.with_context(
                {'default_partner': self.delivery.partner_id.id}).onchange_goods_id()

            break

    def test_inverse_price(self):
        '''由不含税价反算含税价，保存时生效'''
        for line in self.new_delivery.line_out_ids:
            line.price = 10
            self.assertAlmostEqual(line.price_taxed, 11.7)

    def test_onchange_price(self):
        '''当订单行的不含税单价改变时，改变含税单价'''
        for line in self.new_delivery.line_out_ids:
            line.price = 10
            line.onchange_price()
            self.assertAlmostEqual(line.price_taxed, 11.7)
