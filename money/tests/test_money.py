# -*- coding: utf-8 -*-

from openerp.tests.common import TransactionCase
from openerp.exceptions import except_orm


class test_money_order(TransactionCase):
    '''测试收付款'''
    def test_money_order_unlink(self):
        '''测试收付款单删除'''
        self.env.ref('money.get_40000').money_order_done()
        # 审核后不能删除
        with self.assertRaises(except_orm):
            self.env.ref('money.get_40000').unlink()
        # 未审核，可以删除
        self.env.ref('money.pay_2000').unlink()

    def test_money_order_draft(self):
        ''' 测试收付款反审核  '''
        last_balance = self.env.ref('core.comm').balance
        jd_receivable = self.env.ref('core.jd').receivable
        lenovo_payable = self.env.ref('core.lenovo').payable
        # 先收款后付款。收款账户余额增加，业务伙伴应收款减少；
        # 付款账户余额减少，业务伙伴应付款减少
        self.env.ref('money.get_40000').money_order_done()
        self.assertEqual(
            self.env.ref('core.jd').receivable,
            jd_receivable - 40000)
        self.env.ref('money.pay_2000').money_order_done()
        self.assertEqual(
            self.env.ref('core.comm').balance,
            last_balance + 40000 - 2000)
        self.assertEqual(
            self.env.ref('core.lenovo').payable,
            lenovo_payable - 2000)
        # 余额不足不能反审核
        with self.assertRaises(except_orm):
            self.env.ref('money.get_40000').money_order_draft()
        # 反审核付款'money.pay_2000'，账户余额增加，业务伙伴应付款增加
        self.env.ref('money.pay_2000').money_order_draft()
        self.assertEqual(
            self.env.ref('core.comm').balance,
            last_balance + 40000 - 2000 + 2000)
        self.assertEqual(
            self.env.ref('core.lenovo').payable,
            lenovo_payable - 2000 + 2000)

    def test_money_order_onchange(self):
        '''测试收付款onchange'''
        # onchange_date  'get','pay'
        self.env.ref('money.get_40000').with_context({'type': 'get'}) \
            .onchange_date()
        self.env.ref('money.pay_2000').with_context({'type': 'pay'}) \
            .onchange_date()
        # onchange_partner_id 执行self.env.context.get('type') == 'get'
        self.env.ref('money.get_40000').with_context({'type': 'get'}) \
            .onchange_partner_id()
        # onchange_partner_id 执行self.env.context.get('type') == 'pay'
        self.env.ref('money.pay_2000').with_context({'type': 'pay'}) \
            .onchange_partner_id()
        # onchange_partner_id 执行partner_id为空，return
        self.partner_id = False
        self.env['money.order'].onchange_partner_id()

    def test_money_order_done(self):
        ''' 测试收付款审核  '''
        # 余额不足不能付款
        with self.assertRaises(except_orm):
            self.env.ref('money.pay_2000').money_order_done()
        # 收款
        self.env.ref('money.get_40000').money_order_done()
        # 执行money_order_draft 遍历source_ids的操作
        invoice = self.env['money.invoice'].create({
            'partner_id': self.env.ref('core.jd').id,
            'name': 'invoice/2016001',
            'category_id': self.env.ref('money.core_category_sale').id,
            'amount': 200.0,
            'reconciled': 0,
            'to_reconcile': 200.0,
            'date_due': '2016-09-07'})
        money = self.env['money.order'].with_context({'type': 'get'}) \
            .create({
                'partner_id': self.env.ref('core.jd').id,
                'name': 'GET/2016001',
                'note': 'zxy note',
                'line_ids': [(0, 0, {
                    'bank_id': self.env.ref('core.comm').id,
                    'amount': 200.0, 'note': 'money note'})],
                'source_ids': [(0, 0, {
                    'name': invoice.id,
                    'category_id': self.env.ref('money.core_category_sale').id,
                    'date': '2016-04-07',
                    'amount': 200.0,
                    'reconciled': 0,
                    'to_reconcile': 200.0,
                    'this_reconcile': 200.0,
                    'date_due': '2016-09-07'})],
                'type': 'get'})
        money.money_order_done()
        money.money_order_draft()
        # to_reconcile < this_concile, 执行'本次核销金额不能大于未核销金额'
        money.source_ids.to_reconcile = 100.0
        with self.assertRaises(except_orm):
            money.money_order_done()
        self.partner_id = self.env.ref('core.jd')
        money.onchange_partner_id()
        # advance_payment < 0, 执行'核销金额不能大于付款金额'
        self.env.ref('money.pay_2000').line_ids.amount = -10.0
        with self.assertRaises(except_orm):
            self.env.ref('money.pay_2000').money_order_done()


class test_other_money_order(TransactionCase):
    '''测试其他收支单'''
    def test_other_money_order_unlink(self):
        '''测试其他收支单删除'''
        self.env.ref('money.other_get_60').other_money_done()
        # 审核状态不可删除
        with self.assertRaises(except_orm):
            self.env.ref('money.other_get_60').unlink()
        # 未审核可以删除
        self.env.ref('money.other_pay_9000').unlink()

    def test_other_money_order_draft(self):
        ''' 测试其他收入支出反审核'''
        self.env.ref('money.get_40000').money_order_done()
        self.env.ref('money.other_pay_1000').other_money_done()
        self.env.ref('money.other_get_60').other_money_done()
        # 反审核
        self.env.ref('money.other_pay_1000').other_money_draft()
        # 反审核：收款退款余额不足，不能付款
        self.env.ref('money.other_get_60').line_ids.amount = 45000
        with self.assertRaises(except_orm):
            self.env.ref('money.other_get_60').other_money_draft()

    def test_other_money_order(self):
        ''' 测试其他收入支出 '''
        self.env.ref('money.other_get_60').other_money_done()
        # 审核：余额不足，不能付款
        with self.assertRaises(except_orm):
            self.env.ref('money.other_pay_9000').other_money_done()
        # 审核：转出账户收一笔款
        self.env.ref('money.get_40000').money_order_done()
        self.env.ref('money.other_pay_1000').other_money_done()
        # onchange_date  同时执行create时的type=other_get
        invoice = self.env['money.invoice'].create({
            'name': 'invoice',
            'partner_id': self.env.ref('core.jd').id,
            'category_id': self.env.ref('money.core_category_sale').id,
            'amount': 10.0,
            'reconciled': 0})
        other = self.env['other.money.order'] \
            .with_context({'type': 'other_get'}) \
            .create({
                'partner_id': self.env.ref('core.jd').id,
                'bank_id': self.env.ref('core.comm').id,
                'line_ids': [(0, 0, {
                    'source_id': invoice.id,
                    'category_id': self.env.ref('money.core_category_sale').id,
                    'amount': 10.0})]})
        other.onchange_date()
        # 执行other_money_done中存在source_id的情况
        with self.assertRaises(except_orm):  # 执行amount大于源单的未核销金额时的if
            other.other_money_done()
        # 执行amount不大于源单的未核销金额
        invoice.to_reconcile = 10.0
        other.other_money_done()
        other.other_money_draft()
        # onchange_date 执行type=other_pay
        invoice.partner_id = self.env.ref('core.lenovo').id,
        other = self.env['other.money.order'] \
            .with_context({'type': 'other_pay'}) \
            .create({
                'partner_id': self.env.ref('core.lenovo').id,
                'bank_id': self.env.ref('core.comm').id})
        other.onchange_date()
        # onchange_partner
        self.env.ref('money.other_get_60').onchange_partner()
        # 测试其他收支单金额<0,执行if报错
        other = self.env['other.money.order'].create({
            'partner_id': self.env.ref('core.jd').id,
            'bank_id': self.env.ref('core.comm').id,
            'type': 'other_get'})
        self.env['other.money.order.line'].create({
            'other_money_id': other.id,
            'category_id': self.env.ref('money.core_category_sale').id,
            'amount': -10.0})
        with self.assertRaises(except_orm):
            other.other_money_done()


class test_money_transfer_order(TransactionCase):
    '''测试其他资金转账单'''
    def test_money_transfer_order_unlink(self):
        '''测试资金转账单删除'''
        self.env.ref('money.get_40000').money_order_done()
        self.env.ref('money.transfer_300').money_transfer_done()
        # 已审核的转账单不能删除
        with self.assertRaises(except_orm):
            self.env.ref('money.transfer_300').unlink()
        # 未审核的转账单可以删除
        self.env.ref('money.transfer_400').unlink()

    def test_money_transfer_order_draft(self):
        '''测试资金转账单反审核'''
        self.env.ref('money.get_40000').money_order_done()
        self.env.ref('money.transfer_300').money_transfer_done()
        # 反审核
        self.env.ref('money.transfer_300').money_transfer_draft()
        # 转入账户余额不足，不能反审核
        self.env.ref('core.alipay').balance = \
            self.env.ref('core.alipay').balance - 100
        with self.assertRaises(except_orm):
            self.env.ref('money.transfer_400').money_transfer_draft()

    def test_money_transfer_order(self):
        ''' 测试转账单审核 '''
        comm_balance = self.env.ref('core.comm').balance
        money_transfer_300 = self.env.ref('money.transfer_300')
        with self.assertRaises(except_orm):
            # 转出账户余额不足
            money_transfer_300.money_transfer_done()
        # 转出账户收一笔款
        self.env.ref('money.get_40000').money_order_done()
        # 审核
        money_transfer_300.money_transfer_done()
        self.assertEqual(
            self.env.ref('core.comm').balance,
            comm_balance + 40000 - 300)
        self.assertEqual(
            self.env.ref('core.alipay').balance,
            comm_balance + 300)
        # line_ids不存在，则审核报错
        transfer_order = self.env['money.transfer.order']
        transfer_no_line = transfer_order.create({'note': 'no line'})
        with self.assertRaises(except_orm):
            transfer_no_line.money_transfer_done()
        # 转出转入账户相同，则审核报错
        money_transfer_300.line_ids.out_bank_id = \
            self.env.ref('core.alipay').id
        with self.assertRaises(except_orm):
            money_transfer_300.money_transfer_done()
        # 转出金额<0，则审核报错
        money_transfer_300.line_ids.out_bank_id = self.env.ref('core.comm').id
        money_transfer_300.line_ids.amount = -10.0
        with self.assertRaises(except_orm):
            money_transfer_300.money_transfer_done()


class test_partner(TransactionCase):
    def test_partner(self):
        ''' 客户、供应商对账单 和  银行帐'''
        self.env.ref('core.jd').partner_statements()
        self.env.ref('core.lenovo').partner_statements()
        self.env.ref('core.comm').bank_statements()


class test_go_live_order(TransactionCase):
    def test_go_live_order(self):
        '''期初余额'''
        self.env['go.live.order'].create({
            'bank_id': self.env.ref('core.comm').id,
            'balance': 20.0})
        self.env['go.live.order'].create({
            'partner_id': self.env.ref('core.jd').id,
            'receivable': 100.0})
        self.env['go.live.order'].create({
            'partner_id': self.env.ref('core.lenovo').id,
            'payable': 200.0})
