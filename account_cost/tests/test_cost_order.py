# -*- coding: utf-8 -*-
from odoo.tests.common import TransactionCase
from odoo.exceptions import UserError


class TestCostOrder(TransactionCase):
    def setUp(self):
        super(TestCostOrder, self).setUp()

        self.cost_order_1 = self.env.ref('account_cost.cost_order_1')
        self.cost_order_1.partner_id = self.env.ref('core.zt')

        self.buy_order_1 = self.env.ref('buy.buy_order_1')
        self.buy_order_1.buy_order_done()
        self.receipt = self.env['buy.receipt'].search(
            [('order_id', '=', self.buy_order_1.id)])

        self.sell_order_1 = self.env.ref('sell.sell_order_1')
        self.env.ref('sell.sell_order_line_1').tax_rate = 0
        self.sell_order_1.sell_order_done()
        self.delivery = self.env['sell.delivery'].search(
            [('order_id', '=', self.sell_order_1.id)])

    def test_cost_order_confim(self):
        ''' 测试 服务订单 审核 '''
        # no name
        self.cost_order_1.name = ''
        self.cost_order_1.cost_order_confim()
        # 重复审核
        with self.assertRaises(UserError):
            self.cost_order_1.cost_order_confim()

    def test_cost_order_confim_cancel_then_confirm(self):
        ''' 测试 服务订单 审核终止的订单'''
        self.cost_order_1.state = 'cancel'
        # 不能审核已中止的订单
        with self.assertRaises(UserError):
            self.cost_order_1.cost_order_confim()

    def test_cost_order_confim_no_line(self):
        ''' 测试 服务订单 审核 没有明细行'''
        # no line_ids
        self.cost_order_1.line_ids.unlink()
        with self.assertRaises(UserError):
            self.cost_order_1.cost_order_confim()

    def test_cost_order_confim_has_prepayment_no_bank(self):
        ''' 测试 服务订单 审核 有预付没有结算账户 '''
        # 有预付款，但没有结算账户
        self.cost_order_1.prepayment = 10
        with self.assertRaises(UserError):
            self.cost_order_1.cost_order_confim()

    def test_confim_generate_payment_order(self):
        ''' 测试 服务订单 审核 生成付款单 '''
        self.cost_order_1.prepayment = 10
        self.cost_order_1.bank_account_id = self.env.ref('core.alipay')
        self.cost_order_1.cost_order_confim()

    def test_cost_order_draft(self):
        ''' 测试 服务订单 审核 '''
        self.cost_order_1.cost_order_confim()
        self.cost_order_1.cost_order_draft()
        # 重复反审核
        with self.assertRaises(UserError):
            self.cost_order_1.cost_order_draft()

    def test_unlink(self):
        '''删除服务订单'''
        # 不能删除审核过的
        self.cost_order_1.cost_order_confim()
        with self.assertRaises(UserError):
            self.cost_order_1.unlink()
        # 删除草稿的
        self.cost_order_1.cost_order_draft()
        self.cost_order_1.unlink()

    def test_create_mv_cost(self):
        '''在所关联的入库单/发货单上创建费用行'''
        # 关联入库单
        self.cost_order_1.wh_move_ids = [(4, self.receipt.buy_move_id.id)]
        self.cost_order_1.cost_order_confim()

        # 关联发货单
        self.cost_order_1.cost_order_draft()
        self.cost_order_1.wh_move_ids = [(4, self.delivery.sell_move_id.id)]
        self.cost_order_1.cost_order_confim()

    def test_cost_order_draft_has_prepayment(self):
        '''反审核服务订单'''
        # 账户先收钱
        get_money = self.env.ref('money.get_40000')
        get_money.money_order_done()

        self.cost_order_1.prepayment = 20
        self.cost_order_1.bank_account_id = self.env.ref('core.comm')
        self.cost_order_1.cost_order_confim()
        # 找到对应的预收款单，并审核
        money_order = self.env['money.order'].search(
            [('origin_name', '=', self.cost_order_1.name)])
        if money_order:
            money_order.money_order_done()

        # 反审核时，会找到已审核的预收款单，反审核并删除
        self.cost_order_1.cost_order_draft()


class TestCostOrderLine(TransactionCase):

    def setUp(self):
        super(TestCostOrderLine, self).setUp()
        self.cost_order_1 = self.env.ref('account_cost.cost_order_1')

    def test_compute_all_amount(self):
        '''计算价税合计'''
        self.cost_order_1.line_ids[0].amount = 100
        self.assertAlmostEqual(self.cost_order_1.line_ids[0].subtotal, 110.0)
