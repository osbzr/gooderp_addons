# -*- coding: utf-8 -*-
from odoo.tests.common import TransactionCase
from odoo.exceptions import UserError


class TestCustomerStatements(TransactionCase):
    '''测试客户对账单'''

    def setUp(self):
        '''客户账单向导及数据'''
        super(TestCustomerStatements, self).setUp()

        self.env.ref('core.goods_category_1').account_id = self.env.ref(
            'finance.account_goods').id
        self.env.ref('warehouse.wh_in_whin0').date = '2016-02-06'

        # 业务伙伴对账单向导: self._context.get('default_customer')
        self.statement = self.env['partner.statements.report.wizard'].create(
            {'partner_id': self.env.ref('core.jd').id,
             'from_date': '2016-01-01',
             'to_date': '2016-11-01'}).with_context({'default_customer': True})

        # 客户期初余额，查看原始单据应报错
        self.env.ref('core.jd').receivable_init = 1000
        # 创建收款记录
        money_get = self.env.ref('money.get_40000')
        money_get.money_order_done()
        # 创建销售出货单记录
        self.env.ref('warehouse.wh_move_line_14').goods_uos_qty = 200
        self.env.ref(
            'warehouse.wh_move_line_14').production_date = '2016-02-04'
        self.env.ref('warehouse.wh_move_line_14').action_done()
        sell_order = self.env.ref('sell.sell_order_2')
        sell_order.sell_order_done()
        # 因为下面要用到 商品在系统里面必须是有数量的 所以,找到一个简单的方式直接确认已有的盘点单
        warehouse_obj = self.env.ref('warehouse.wh_in_whin0')
        warehouse_obj.approve_order()

        receipt = self.env['sell.delivery'].search(
            [('order_id', '=', sell_order.id)])
        receipt.sell_delivery_done()
        invoice = self.env['money.invoice'].search(
            [('name', '=', receipt.name)])

        # 创建销售退货单记录
        sell_return = self.env.ref('sell.sell_order_return')
        sell_return.sell_order_done()
        receipt_return = self.env['sell.delivery'].search(
            [('order_id', '=', sell_return.id)])
        receipt_return.sell_delivery_done()

    def test_customer_statements_wizard(self):
        '''客户对账单向导'''
        # 测试客户对账单方法中的'结束日期不能小于开始日期！'
        self.statement.from_date = '2016-11-03'
        with self.assertRaises(UserError):
            self.statement.partner_statements_without_goods()
        with self.assertRaises(UserError):
            self.statement.partner_statements_with_goods()
        # 测试客户对账单方法中的from_date的默认值是否是公司启用日期
        statement_date = self.env['partner.statements.report.wizard'].create({'partner_id': self.env.ref('sell.sell_order_1').partner_id.id,
                                                                              'to_date': '2016-11-03'})
        self.assertEqual(statement_date.from_date,
                         self.env.user.company_id.start_date)

    def test_customer_statements_find_source(self):
        '''查看客户对账单明细'''
        # 查看客户对账单明细不带商品明细
        self.statement.partner_statements_without_goods()
        customer_statement = self.env['customer.statements.report'].search([])
        customer_statement_init = self.env['customer.statements.report'].search([('move_id', '=', False),
                                                                                 ('amount', '!=', 0)])
        # 如果对账单中是期初余额行，点击查看按钮应报错
        with self.assertRaises(UserError):
            customer_statement_init.find_source_order()

        for report in list(set(customer_statement) - set(customer_statement_init)):
            report.find_source_order()

        # 查看客户对账单带商品明细
        self.statement.partner_statements_with_goods()
        customer_statement_goods = self.env['customer.statements.report.with.goods'].search([
                                                                                            ('name', '!=', False)])
        customer_statement_goods_init = self.env['customer.statements.report.with.goods'].search([('move_id', '=', False),
                                                                                                  ('amount', '!=', 0)])

        # 如果对账单中是期初余额行，点击查看按钮应报错
        with self.assertRaises(UserError):
            customer_statement_goods_init.find_source_order()

        for report in list(set(customer_statement_goods) - set(customer_statement_goods_init)):
            self.assertNotEqual(str(report.balance_amount), 'kaihe11')
            report.find_source_order()


class TestTrackWizard(TransactionCase):
    '''测试销售订单跟踪表向导'''

    def setUp(self):
        ''' 准备报表数据 '''
        super(TestTrackWizard, self).setUp()
        self.env.ref('core.jd').credit_limit = 100000
        self.env.ref('core.goods_category_1').account_id = self.env.ref(
            'finance.account_goods').id
        self.env.ref('warehouse.wh_in_whin0').date = '2016-02-06'

        # 补足商品网线的数量
        warehouse_obj = self.env.ref('warehouse.wh_in_whin0')
        warehouse_obj.approve_order()

        self.order = self.env.ref('sell.sell_order_2')
        order_2 = self.order.copy()
        order_2.sell_order_done()
        # 分批出库
        delivery_2 = self.env['sell.delivery'].search(
            [('order_id', '=', order_2.id)])
        for line in delivery_2.line_out_ids:
            line.goods_qty = 5
        delivery_2.sell_delivery_done()
        delivery_3 = self.env['sell.delivery'].search(
            [('order_id', '=', order_2.id), ('state', '=', 'draft')])
        delivery_3.sell_delivery_done()

        # 销货订单产生退货单
        sell_return = self.env.ref('sell.sell_order_return')
        sell_return.sell_order_done()

        self.track_obj = self.env['sell.order.track.wizard']
        self.track = self.track_obj.create({})

    def test_button_ok(self):
        '''测试销售订单跟踪表  确认按钮'''
        # 日期报错
        track = self.track_obj.create({
            'date_start': '2016-11-01',
            'date_end': '2016-1-01',
        })
        with self.assertRaises(UserError):
            track.button_ok()
        # 按日期搜索
        self.track.button_ok()
        # 按商品、客户、销售员、仓库搜索
        self.track.goods_id = self.env.ref('goods.mouse').id
        self.track.partner_id = self.env.ref('core.yixun').id
        self.track.user_id = self.env.ref('base.user_demo').id
        self.track.warehouse_id = self.env.ref('warehouse.hd_stock').id
        self.track.button_ok()

    def test_view_detail(self):
        '''测试销售订单跟踪表  查看明细按钮'''

        self.env.ref('core.goods_category_1').account_id = self.env.ref(
            'finance.account_goods').id

        self.track.button_ok()
        goods_id = self.env.ref('goods.cable').id
        track_line = self.env['sell.order.track'].search(
            [('goods_id', '=', goods_id)])
        track_line[0].view_detail()


class TestDetailWizard(TransactionCase):
    '''测试销售订单明细表向导'''

    def setUp(self):
        ''' 准备报表数据 '''
        super(TestDetailWizard, self).setUp()
        self.env.ref('core.jd').credit_limit = 100000
        self.env.ref('core.goods_category_1').account_id = self.env.ref(
            'finance.account_goods').id
        self.env.ref('warehouse.wh_in_whin0').date = '2016-02-06'

        # 补足商品网线的数量
        warehouse_obj = self.env.ref('warehouse.wh_in_whin0')
        warehouse_obj.approve_order()
        # 复制一张销货订单并审核
        self.order = self.env.ref('sell.sell_order_2')
        order_2 = self.order.copy()
        order_2.sell_order_done()

        # 审核出库单
        delivery_2 = self.env['sell.delivery'].search(
            [('order_id', '=', order_2.id)])
        delivery_2.sell_delivery_done()

        # 销货订单产生退货单，并审核退货单
        sell_return = self.env.ref('sell.sell_order_return')
        sell_return.sell_order_done()
        delivery_return = self.env['sell.delivery'].search(
            [('order_id', '=', sell_return.id)])
        delivery_return.sell_delivery_done()

        self.detail_obj = self.env['sell.order.detail.wizard']
        self.detail = self.detail_obj.create({})

    def test_button_ok(self):
        '''测试销售订单明细表  确认按钮'''

        self.env.ref('core.goods_category_1').account_id = self.env.ref(
            'finance.account_goods').id

        detail = self.detail_obj.create({
            'date_start': '2016-11-01',
            'date_end': '2016-1-01',
        })
        with self.assertRaises(UserError):
            detail.button_ok()
        # 按日期搜索
        self.detail.button_ok()
        # 按商品、客户、销售员、仓库搜索
        self.detail.goods_id = self.env.ref('goods.mouse').id
        self.detail.partner_id = self.env.ref('core.yixun').id
        self.detail.user_id = self.env.ref('base.user_demo').id
        self.detail.warehouse_id = self.env.ref('warehouse.hd_stock').id
        self.detail.button_ok()

    def test_view_detail(self):
        '''测试销售订单明细表  查看明细按钮'''
        self.detail.button_ok()
        goods_id = self.env.ref('goods.cable').id
        detail_line = self.env['sell.order.detail'].search(
            [('goods_id', '=', goods_id)])
        for line in detail_line:
            line.view_detail()


class TestGoodsWizard(TransactionCase):
    '''测试销售汇总表（按商品）向导'''

    def setUp(self):
        ''' 准备报表数据 '''
        super(TestGoodsWizard, self).setUp()
        self.env.ref('core.jd').credit_limit = 100000
        self.env.ref('core.goods_category_1').account_id = self.env.ref(
            'finance.account_goods').id
        self.env.ref('warehouse.wh_in_whin0').date = '2016-02-06'

        warehouse_obj = self.env.ref('warehouse.wh_in_whin0')
        warehouse_obj.approve_order()
        self.order = self.env.ref('sell.sell_order_2')
        self.order.sell_order_done()
        self.delivery = self.env['sell.delivery'].search(
            [('order_id', '=', self.order.id)])
        self.delivery.sell_delivery_done()
        self.goods_wizard_obj = self.env['sell.summary.goods.wizard']
        self.goods_wizard = self.goods_wizard_obj.create({})

    def test_button_ok(self):
        '''销售汇总表（按商品）向导确认按钮'''
        # 日期报错
        goods_wizard = self.goods_wizard_obj.create({
            'date_start': '2016-11-01',
            'date_end': '2016-1-01',
        })
        with self.assertRaises(UserError):
            goods_wizard.button_ok()
        # 按日期搜索
        self.goods_wizard.button_ok()

    def test_goods_report(self):
        '''测试销售汇总表（按商品）报表'''
        summary_goods = self.env['sell.summary.goods'].create({})
        context = self.goods_wizard.button_ok().get('context')
        results = summary_goods.with_context(context).search_read(domain=[])
        new_goods_wizard = self.goods_wizard.copy()
        new_goods_wizard.goods_id = self.env.ref('goods.mouse').id
        new_goods_wizard.partner_id = self.env.ref('core.jd').id
        new_goods_wizard.goods_categ_id = \
            self.env.ref('core.goods_category_1').id
        new_goods_wizard.warehouse_id = self.env.ref('warehouse.hd_stock').id
        new_context = new_goods_wizard.button_ok().get('context')
        new_results = summary_goods.with_context(new_context).search_read(
            domain=[])
        self.assertEqual(len(results), 1)
        self.assertEqual(len(new_results), 0)

    def test_view_detail(self):
        '''销售汇总表（按商品）  查看明细按钮'''
        summary_goods = self.env['sell.summary.goods'].create({})
        context = self.goods_wizard.button_ok().get('context')
        results = summary_goods.with_context(context).search_read(domain=[])
        for line in results:
            summary_line = summary_goods.browse(line['id'])
            summary_line.with_context(context).view_detail()


class TestPartnerWizard(TransactionCase):
    '''测试销售汇总表（按客户）向导'''

    def setUp(self):
        ''' 准备报表数据 '''
        super(TestPartnerWizard, self).setUp()
        self.env.ref('core.jd').credit_limit = 100000

        self.env.ref('core.goods_category_1').account_id = self.env.ref(
            'finance.account_goods').id
        self.env.ref('warehouse.wh_in_whin0').date = '2016-02-06'

        warehouse_obj = self.env.ref('warehouse.wh_in_whin0')
        warehouse_obj.approve_order()
        self.order = self.env.ref('sell.sell_order_2')
        self.order.sell_order_done()
        self.delivery = self.env['sell.delivery'].search(
            [('order_id', '=', self.order.id)])
        self.delivery.sell_delivery_done()
        self.partner_wizard_obj = self.env['sell.summary.partner.wizard']
        self.partner_wizard = self.partner_wizard_obj.create({})

    def test_button_ok(self):
        '''销售汇总表（按客户）向导确认按钮'''
        # 日期报错
        partner_wizard = self.partner_wizard_obj.create({
            'date_start': '2016-11-01',
            'date_end': '2016-1-01',
        })
        with self.assertRaises(UserError):
            partner_wizard.button_ok()
        # 按日期搜索
        self.partner_wizard.button_ok()

    def test_partner_report(self):
        '''测试销售汇总表（按客户）报表'''
        summary_partner = self.env['sell.summary.partner'].create({})
        context = self.partner_wizard.button_ok().get('context')
        results = summary_partner.with_context(context).search_read(domain=[])
        new_partner_wizard = self.partner_wizard.copy()
        new_partner_wizard.goods_id = self.env.ref('goods.mouse').id
        new_partner_wizard.partner_id = self.env.ref('core.jd').id
        c_category_id = self.env.ref('core.customer_category_1')    # 客户类别:一级客户
        new_partner_wizard.c_category_id = c_category_id.id
        new_partner_wizard.warehouse_id = self.env.ref('warehouse.hd_stock').id
        new_context = new_partner_wizard.button_ok().get('context')
        new_results = summary_partner.with_context(new_context).search_read(
            domain=[])

    def test_view_detail(self):
        '''销售汇总表（按客户）  查看明细按钮'''
        summary_partner = self.env['sell.summary.partner'].create({})
        context = self.partner_wizard.button_ok().get('context')
        results = summary_partner.with_context(context).search_read(domain=[])
        for line in results:
            summary_line = summary_partner.browse(line['id'])
            summary_line.with_context(context).view_detail()


class TestStaffWizard(TransactionCase):
    '''测试销售汇总表（按销售人员）向导'''

    def setUp(self):
        ''' 准备报表数据 '''
        super(TestStaffWizard, self).setUp()
        self.env.ref('core.jd').credit_limit = 100000
        self.env.ref('core.goods_category_1').account_id = self.env.ref(
            'finance.account_goods').id
        self.env.ref('warehouse.wh_in_whin0').date = '2016-02-06'
        warehouse_obj = self.env.ref('warehouse.wh_in_whin0')
        warehouse_obj.approve_order()
        self.order = self.env.ref('sell.sell_order_2')
        self.order.sell_order_done()
        self.delivery = self.env['sell.delivery'].search(
            [('order_id', '=', self.order.id)])
        self.delivery.sell_delivery_done()
        self.staff_wizard_obj = self.env['sell.summary.staff.wizard']
        self.staff_wizard = self.staff_wizard_obj.create({})

    def test_button_ok(self):
        '''销售汇总表（按销售人员）向导确认按钮'''
        # 日期报错
        staff_wizard = self.staff_wizard_obj.create({
            'date_start': '2016-11-01',
            'date_end': '2016-1-01',
        })
        with self.assertRaises(UserError):
            staff_wizard.button_ok()
        # 按日期搜索
        self.staff_wizard.button_ok()

    def test_staff_report(self):
        '''测试销售汇总表（按销售人员）报表'''
        summary_staff = self.env['sell.summary.staff'].create({})
        context = self.staff_wizard.button_ok().get('context')
        results = summary_staff.with_context(context).search_read(domain=[])

        new_staff_wizard = self.staff_wizard.copy()
        new_staff_wizard.user_id = self.env.ref('base.user_demo').id
        new_staff_wizard.goods_id = self.env.ref('goods.cable').id
        new_staff_wizard.goods_categ_id = \
            self.env.ref('core.goods_category_1').id
        new_staff_wizard.warehouse_id = self.env.ref('warehouse.hd_stock').id
        new_context = new_staff_wizard.button_ok().get('context')
        new_results = summary_staff.with_context(new_context).search_read(
            domain=[])

    def test_view_detail(self):
        '''销售汇总表（按销售人员）  查看明细按钮'''
        summary_staff = self.env['sell.summary.staff'].create({})
        context = self.staff_wizard.button_ok().get('context')
        results = summary_staff.with_context(context).search_read(domain=[])
        for line in results:
            summary_line = summary_staff.browse(line['id'])
            summary_line.with_context(context).view_detail()


class TestReceiptWizard(TransactionCase):
    '''测试销售收款一览表向导'''

    def setUp(self):
        ''' 准备报表数据 '''
        super(TestReceiptWizard, self).setUp()

        self.env.ref('core.goods_category_1').account_id = self.env.ref(
            'finance.account_goods').id
        self.env.ref('warehouse.wh_in_whin0').date = '2016-02-06'

        warehouse_obj = self.env.ref('warehouse.wh_in_whin0')
        warehouse_obj.approve_order()

        # 销货订单产生发货单，并审核发货单产生收款单
        self.order = self.env.ref('sell.sell_order_2')
        self.order.sell_order_done()
        self.delivery = self.env['sell.delivery'].search(
            [('order_id', '=', self.order.id)])
        self.delivery.bank_account_id = self.env.ref('core.comm')
        self.env.ref('money.get_40000').money_order_done()
        self.delivery.receipt = 2.0
        self.delivery.sell_delivery_done()

        # 销货订单产生发货单，并审核发货单，成交金额和本次收款均为0
        new_delivery = self.delivery.copy()
#         new_delivery.discount_amount = (new_delivery.amount
#                                         + new_delivery.discount_amount)
        new_delivery.receipt = 0
        new_delivery.bank_account_id = False
        new_delivery.sell_delivery_done()

        # 销货订单产生退货单，并审核退货单
        self.order_return = self.env.ref('sell.sell_order_return')
        self.order_return.sell_order_done()
        self.delivery_return = self.env['sell.delivery'].search(
            [('order_id', '=', self.order_return.id)])
        self.delivery_return.sell_delivery_done()
        self.receipt_wizard_obj = self.env['sell.receipt.wizard']
        self.receipt_wizard = self.receipt_wizard_obj.create({})

    def test_button_ok(self):
        '''测试销售收款一览表  确认按钮'''

        self.env.ref('core.goods_category_1').account_id = self.env.ref(
            'finance.account_goods').id

        # 日期报错
        receipt_wizard = self.receipt_wizard_obj.create({
            'date_start': '2016-11-01',
            'date_end': '2016-1-01',
        })
        with self.assertRaises(UserError):
            receipt_wizard.button_ok()
        # 按日期搜索
        self.receipt_wizard.button_ok()
        # 按客户类别、客户、销售员、仓库搜索
        self.receipt_wizard.c_category_id = \
            self.env.ref('core.customer_category_1').id
        self.receipt_wizard.partner_id = self.env.ref('core.jd').id
        self.receipt_wizard.user_id = self.env.ref('base.user_demo').id
        self.receipt_wizard.warehouse_id = self.env.ref(
            'warehouse.hd_stock').id
        self.receipt_wizard.button_ok()

    def test_view_detail(self):
        '''测试销售收款一览表  查看明细按钮'''
        self.receipt_wizard.button_ok()
        self.env.ref('core.goods_category_1').account_id = self.env.ref(
            'finance.account_goods').id

        receipt_line = self.env['sell.receipt'].search(
            [('order_name', '=', self.delivery.name)])
        for line in receipt_line:
            line.view_detail()
        receipt_line2 = self.env['sell.receipt'].search(
                                [('order_name', '=', self.delivery_return.name)])
        for line in receipt_line2:
            line.view_detail()

    def test_generate_reconcile_order(self):
        '''新建核销单，应收冲预收，客户为所选行客户'''
        self.receipt_wizard.button_ok()
        for line in self.env['sell.receipt'].search([
            ('order_name', '=', u'未核销预收款'), ('receipt', '!=', 0)]):
            line.generate_reconcile_order()
            # 查看生成的核销单
            line.generate_reconcile_order()

class TestSellTopTenWizard(TransactionCase):
    '''测试销量前十商品向导'''

    def setUp(self):
        ''' 准备报表数据 '''
        super(TestSellTopTenWizard, self).setUp()
        self.env.ref('core.jd').credit_limit = 100000
        self.env.ref('core.goods_category_1').account_id = self.env.ref(
            'finance.account_goods').id
        self.env.ref('warehouse.wh_in_whin0').date = '2016-02-06'

        warehouse_obj = self.env.ref('warehouse.wh_in_whin0')
        warehouse_obj.approve_order()
        self.order = self.env.ref('sell.sell_order_2')
        self.order.sell_order_done()
        self.delivery = self.env['sell.delivery'].search(
            [('order_id', '=', self.order.id)])
        self.delivery.sell_delivery_done()
        self.wizard_obj = self.env['sell.top.ten.wizard']
        self.wizard = self.wizard_obj.create({
            'date_start': '2016-1-01',
            'date_end': '2016-12-12', })

    def test_button_ok(self):
        '''销量前十商品向导确认按钮'''
        # 日期报错
        wizard = self.wizard.create({
            'date_start': '2016-11-01',
            'date_end': '2016-1-01',
        })
        with self.assertRaises(UserError):
            wizard.button_ok()
        # 日期默认值
        self.wizard_obj.create({})

    def test_goods_report(self):
        '''测试销量前十商品报表'''
        summary_top_ten = self.env['sell.top.ten'].create({})
        context = self.wizard.button_ok().get('context')
        results = summary_top_ten.with_context(context).search_read(domain=[])

        new_wizard = self.wizard.copy()
        new_wizard.warehouse_id = self.env.ref('warehouse.hd_stock').id
        new_context = new_wizard.button_ok().get('context')
        new_results = summary_top_ten.with_context(new_context).search_read(
            domain=[])

        self.assertEqual(len(results), 1)
        self.assertEqual(len(new_results), 1)


class TestPopupWizard(TransactionCase):
    '''发货单缺货向导'''

    def setUp(self):
        ''' 准备数据 '''
        super(TestPopupWizard, self).setUp()
        self.env.ref('core.jd').credit_limit = 100000
        self.order = self.env.ref('sell.sell_order_2')
        self.order.sell_order_done()
        self.delivery = self.env['sell.delivery'].search(
            [('order_id', '=', self.order.id)])
        self.hd_stock = self.env.ref('warehouse.hd_stock')
        self.warehouse_inventory = self.env.ref(
            'warehouse.warehouse_inventory')
