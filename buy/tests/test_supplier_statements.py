# -*- coding: utf-8 -*-
from odoo.tests.common import TransactionCase
from odoo.exceptions import UserError


class TestSupplierStatements(TransactionCase):
    '''测试供应商对账单'''

    def setUp(self):
        '''供应商对账单向导及数据'''
        super(TestSupplierStatements, self).setUp()
        # 业务伙伴对账单向导: else self._context.get('default_supplier')
        objStatements = self.env['partner.statements.report.wizard']
        self.statement = objStatements.create({
            'partner_id': self.env.ref('core.lenovo').id,
            'from_date': '2016-01-01',
            'to_date': '2016-11-01'}).with_context({'default_supplier': True})

        # 供应商期初余额，查看原始单据应报错
        self.env.ref('core.lenovo').payable_init = 1000
        partner = self.env['partner'].search(
            [('id', '=', self.env.ref('core.lenovo').id)])

        # 创建付款记录
        money_get = self.env.ref('money.get_40000')
        money_get.money_order_done()
        money_order = self.env.ref('money.pay_2000')
        money_order.money_order_done()
        # 给buy_order_1中的商品“键盘”的分类设置科目
        self.env.ref('core.goods_category_1').account_id = self.env.ref(
            'finance.account_goods').id
        # 创建采购入库单记录
        buy_order = self.env.ref('buy.buy_order_1')
        buy_order.bank_account_id = False
        buy_order.buy_order_done()
        objReceipt = self.env['buy.receipt']
        receipt = objReceipt.search([('order_id', '=', buy_order.id)])
        receipt.buy_receipt_done()
        # 创建采购退货单记录
        buy_return = self.env.ref('buy.buy_return_order_1')
        buy_return.bank_account_id = False
        buy_return.buy_order_done()
        receipt_return = objReceipt.search([('order_id', '=', buy_return.id)])
        receipt_return.buy_receipt_done()

    def test_supplier_statements_wizard(self):
        '''供应商对账单向导'''
        # 测试'结束日期不能小于开始日期！'
        self.statement.from_date = '2016-11-03'
        with self.assertRaises(UserError):
            self.statement.partner_statements_without_goods()
        with self.assertRaises(UserError):
            self.statement.partner_statements_with_goods()
        # 测试from_date的默认值是否是公司启用日期
        objStatements = self.env['partner.statements.report.wizard']
        statement_date = objStatements.create({
            'partner_id': self.env.ref('core.lenovo').id,
            'to_date': '2016-11-03'}).with_context({'default_supplier': True})
        self.assertEqual(
            statement_date.from_date,
            self.env.user.company_id.start_date
        )

    def test_supplier_statements_find_source(self):
        '''查看供应商对账单明细'''
        # 查看不带商品明细源单
        self.statement.partner_statements_without_goods()
        supplier_statement = self.env['supplier.statements.report'].search([])
        supplier_statement_init = self.env['supplier.statements.report'].search([('move_id', '=', False),
                                                                                 ('amount', '!=', 0)])
        # 如果对账单中是期初余额行，点击查看按钮应报错
        with self.assertRaises(UserError):
            supplier_statement_init.find_source_order()

        for report in list(set(supplier_statement) - set(supplier_statement_init)):
            report.find_source_order()

        # 查看带商品明细源单
        self.statement.partner_statements_with_goods()
        objGoods = self.env['supplier.statements.report.with.goods']
        supplier_statement_goods = objGoods.search([('name', '!=', False)])
        supplier_statement_goods_init = objGoods.search([('move_id', '=', False),
                                                         ('amount', '!=', 0)])

        # 如果对账单中是期初余额行，点击查看按钮应报错
        with self.assertRaises(UserError):
            supplier_statement_goods_init.find_source_order()

        for report in list(set(supplier_statement_goods) - set(supplier_statement_goods_init)):
            self.assertNotEqual(str(report.balance_amount), 'kaihe11')
            report.find_source_order()


class TestPartner(TransactionCase):
    def test_action_view_buy_history(self):
        """ 测试 供应商购货记录（最近一年）"""
        supplier_lenovo = self.env.ref('core.lenovo')
        supplier_lenovo.action_view_buy_history()
        # 测试 时间间隔大于1年的 if
        self.env.user.company_id.start_date = '2016-01-01'
        supplier_lenovo.action_view_buy_history()