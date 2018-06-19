# -*- coding: utf-8 -*-
from odoo.tests.common import TransactionCase
from odoo.exceptions import UserError, ValidationError


class TestExchange(TransactionCase):
    ''' 测试  期末调汇  汇兑损益 '''

    def setUp(self):
        super(TestExchange, self).setUp()
        self.usd_account = self.env['finance.account'].create({
            'code': '1002001003',
            'name': '银行存款-美元',
            'user_type': self.env.ref('finance.base_assest').id,
            'balance_directions': 'in',
            'currency_id': self.env.ref('base.USD').id,
            'exchange': True,
            'auxiliary_financing': 'customer',
        })
        self.create_exchange_wizard = self.env['create.exchange.wizard'].create({
            'date': '2015-12-08',
        })
        # 借贷方为 外币 币别
        # 2015年12月的凭证 2015-12-08
        self.env.ref('core.jd').c_category_id.account_id.currency_id = self.env.ref('base.USD')
        self.env.ref('core.jd').c_category_id.account_id.exchange = True
        self.env.ref(
            'finance.voucher_line_12_debit').parner_id = self.env.ref('core.jd')
        self.env.ref(
            'finance.voucher_line_12_credit').account_id = self.usd_account
        self.env.ref('finance.voucher_12').voucher_done()
        
        # 相反分录用于测试相反方向发生额
        voucher = self.env['voucher'].create({
            'date': '2015-12-01',
            'line_ids': [(0, 0, {
                'name': u'退投资',  # 贷方行
                'account_id': self.env.ref('core.jd').c_category_id.account_id.id,
                'partner_id': self.env.ref('core.jd').id,
                'debit': 1,
            }),
                (0, 0, {
                    'name': u'退投资',  # 借方行
                    'account_id': self.usd_account.id,
                    'credit': 1,
                })]
        })
        voucher.voucher_done()
        
    def test_create_exchange_in(self):
        '''测试  有辅助核算 余额方向为 借'''
        self.create_exchange_wizard.create_exchange()

    def test_create_exchange_out(self):
        '''测试  有辅助核算  余额方向为 贷'''
        self.usd_account.balance_directions = 'out'
        self.create_exchange_wizard.create_exchange()

    def test_create_exchange_no_auxiliary_financing(self):
        '''测试   无辅助核算 余额方向为 借'''
        self.usd_account.auxiliary_financing = False
        self.create_exchange_wizard.create_exchange()

    def test_create_exchange_no_auxiliary_financing_out(self):
        '''测试  无辅助核算  余额方向为 贷'''
        self.usd_account.auxiliary_financing = False
        self.usd_account.balance_directions = 'out'
        self.create_exchange_wizard.create_exchange()

    def test_default_wizard_date(self):
        ''' 测试向导上默认取当前日期 '''
        date_wizard = self.create_exchange_wizard = self.env['create.exchange.wizard'].create({})
        # 无期末调汇科目
        self.usd_account.currency_id = False
        self.env.ref('core.jd').c_category_id.account_id.currency_id = False
        date_wizard.create_exchange()


