# -*- coding: utf-8 -*-
from odoo.tests.common import TransactionCase
from odoo.exceptions import UserError


class TestAsset(TransactionCase):

    def setUp(self):
        '''固定资产准备数据'''
        super(TestAsset, self).setUp()
        self.asset = self.env.ref('asset.asset_car')

    def test_unlink(self):
        '''测试删除已审核的固定资产'''
        asset = self.asset.copy()
        self.asset.asset_done()
        with self.assertRaises(UserError):
            self.asset.unlink()
        # 删除草稿状态的固定资产
        asset.unlink()

    def test_onchange(self):
        '''资产相关科目由资产类别带出'''
        self.asset.category_id = self.env.ref('asset.house')
        self.asset.onchange_category_id()
        self.asset.cost = 2000
        self.asset.onchange_cost()
        self.asset.partner_id = self.env.ref('core.zt')
        self.asset.onchange_partner_id()
        self.asset.bank_account = self.env.ref('core.alipay')
        self.asset.onchange_bank_account()

    def test_wrong_asset_done_repeat(self):
        '''错误审核: 重复审核'''
        self.asset.asset_done()
        with self.assertRaises(UserError):
            self.asset.asset_done()

    def test_wrong_asset_done_period_closed(self):
        '''错误审核: 该会计期间已结账！不能审核'''
        self.env.ref('finance.period_201604').is_closed = True
        with self.assertRaises(UserError):
            self.asset.asset_done()

    def test_wrong_asset_done_amount(self):
        '''错误审核: 金额必须大于0'''
        self.asset.cost = 0
        with self.assertRaises(UserError):
            self.asset.asset_done()

    def test_wrong_asset_done_tax(self):
        '''错误审核: 税额必须大于0'''
        self.asset.tax = -1
        with self.assertRaises(UserError):
            self.asset.asset_done()

    def test_wrong_asset_done_depreciation_previous(self):
        '''错误审核: 以前折旧必须大于0'''
        self.asset.depreciation_previous = -1
        with self.assertRaises(UserError):
            self.asset.asset_done()

    def test_asset_done_bank_account(self):
        '''选择结算账户，生成其他支出单'''
        self.asset.bank_account = self.env.ref('core.alipay')
        self.asset.onchange_bank_account()
        self.asset.asset_done()

    def test_asset_done_construction(self):
        '''贷方科目选择在建工程，直接生成凭证'''
        self.asset.account_credit = self.env.ref(
            'finance.small_business_chart1604')
        self.asset.asset_done()

    def test_asset_done_money_invoice_not_done(self):
        ''' Test: asset done, but money invoice not done  '''
        self.env.user.company_id.draft_invoice = True
        self.asset.asset_done()

    def test_asset_draft_repeat(self):
        '''反审核报错: 重复反审核'''
        with self.assertRaises(UserError):
            self.asset.asset_draft()

    def test_asset_draft_asset_line(self):
        '''反审核报错: 已折旧不能反审核'''
        self.asset.asset_done()
        wizard = self.env['create.depreciation.wizard'].create(
            {'date': '2016-05-01'})
        wizard._compute_period_id()
        wizard.create_depreciation()
        with self.assertRaises(UserError):
            self.asset.asset_draft()

    def test_asset_draft_change_line(self):
        '''反审核报错: 已变更不能反审核'''
        self.asset.asset_done()
        wizard = self.env['create.chang.wizard'].with_context({'active_id': self.asset.id}).create({
            'chang_date': '2016-04-02',
            'chang_cost': 100,
            'chang_depreciation_number': 1,
            'chang_tax': 17,
            'chang_partner_id': self.env.ref('core.lenovo').id})
        wizard._compute_period_id()
        wizard.create_chang_account()
        with self.assertRaises(UserError):
            self.asset.asset_draft()

    def test_asset_draft_period_closed(self):
        '''反审核报错: 该会计期间已结账！不能反审核'''
        self.asset.asset_done()
        self.env.ref('finance.period_201604').is_closed = True
        with self.assertRaises(UserError):
            self.asset.asset_draft()

    def test_asset_draft_partner(self):
        '''正常反审核：选择往来单位，生成结算单'''
        self.asset.asset_done()
        self.asset.asset_draft()

    def test_asset_draft_bank_account(self):
        '''正常反审核：选择结算账户，生成其他支出单'''
        self.asset.bank_account = self.env.ref('core.alipay')
        self.asset.bank_account.balance = 1000000  # 确保审核其他支出单时账户余额充足
        self.asset.onchange_bank_account()
        self.asset.asset_done()
        other = self.env['other.money.order'].search(
            [('id', '=', self.asset.other_money_order.id)])
        other.other_money_done()
        self.asset.asset_draft()

    def test_asset_draft_construction(self):
        '''正常反审核：贷方科目选择在建工程，直接生成凭证'''
        self.asset.account_credit = self.env.ref(
            'finance.small_business_chart1604')
        self.asset.asset_done()
        self.asset.asset_draft()

    def test_get_cost_depreciation(self):
        ''' Test: _get_cost_depreciation '''
        self.asset.asset_done()
        # 提一次折旧
        wizard = self.env['create.depreciation.wizard'].create({'date': '2016-05-01'})
        wizard.create_depreciation()
        self.asset.depreciation_number = 12

        # 已提完
        self.asset.depreciation_number = 1

    def test_core_category_unlink(self):
        """不能删除系统创建的类别"""
        with self.assertRaises(UserError):
            self.env.ref('asset.asset').unlink()


class TestCreateCleanWizard(TransactionCase):

    def setUp(self):
        '''固定资产清理准备数据'''
        super(TestCreateCleanWizard, self).setUp()
        self.asset = self.env.ref('asset.asset_car')

    def test_compute_period_id(self):
        '''固定资产清理：计算期间'''
        wizard = self.env['create.clean.wizard'].create({
            'date': '2016-04-02',
            'clean_cost': 50,
            'residual_income': 100,
            'sell_tax_amount': 17,
            'bank_account': self.env.ref('core.alipay').id
        })
        wizard._compute_period_id()
        wizard.create_clean_account()

    def test_create_clean_account(self):
        '''清理固定资产'''
        wizard = self.env['create.clean.wizard'].with_context({'active_id': self.asset.id}).create({
            'date': '2016-04-02',
            'clean_cost': 50,
            'residual_income': 100,
            'sell_tax_amount': 17,
            'bank_account': self.env.ref('core.alipay').id
        })
        wizard._compute_period_id()
        wizard.create_clean_account()


class TestCreateChangWizard(TransactionCase):

    def setUp(self):
        '''固定资产变更准备数据'''
        super(TestCreateChangWizard, self).setUp()
        self.asset = self.env.ref('asset.asset_car')

    def test_compute_period_id(self):
        '''固定资产变更：计算期间'''
        wizard = self.env['create.chang.wizard'].create({
            'chang_date': '2016-04-02',
            'chang_cost': 100,
            'chang_depreciation_number': 1,
            'chang_tax': 17,
            'chang_partner_id': self.env.ref('core.lenovo').id
        })
        wizard._compute_period_id()
        wizard.create_chang_account()

    def test_create_chang_account(self):
        '''变更固定资产'''
        wizard = self.env['create.chang.wizard'].with_context({'active_id': self.asset.id}).create({
            'chang_date': '2016-04-02',
            'chang_cost': 100,
            'chang_depreciation_number': 1,
            'chang_tax': 17,
            'chang_partner_id': self.env.ref('core.lenovo').id
        })
        wizard._compute_period_id()

        # 生成的 money invoice 默认没有审核
        self.env.user.company_id.draft_invoice = True
        wizard.create_chang_account()


class TestAssetLine(TransactionCase):

    def setUp(self):
        '''折旧明细准备数据'''
        super(TestAssetLine, self).setUp()
        self.asset = self.env.ref('asset.asset_car')
        self.asset_line = self.env['asset.line'].create({
            'order_id': self.asset.id,
            'date': '2016-04-02',
            'cost_depreciation': 100,
        })
        self.period_201604 = self.env.ref('finance.period_201604')

    def test_compute_period_id(self):
        '''折旧明细计算期间'''
        self.asset_line._compute_period_id()
        self.assertTrue(self.asset_line.period_id == self.period_201604)


class TestDepreciationWizard(TransactionCase):

    def setUp(self):
        '''折旧向导准备数据'''
        super(TestDepreciationWizard, self).setUp()
        self.asset = self.env.ref('asset.asset_car')
        self.wizard = self.env['create.depreciation.wizard'].create(
            {'date': '2016-05-01'})

    def test_get_last_date(self):
        ''' 取本月的最后一天作为默认折旧日 '''
        self.env['create.depreciation.wizard'].create({})

    def test_compute_period_id(self):
        '''资产折旧：计算期间'''
        self.wizard._compute_period_id()

    def test_create_depreciation(self):
        '''资产折旧，生成凭证和折旧明细'''
        self.asset.depreciation_number = 1
        self.asset.depreciation_previous = 950
        with self.assertRaises(UserError):
            self.wizard.create_depreciation()

    def test_create_depreciation_surplusValue(self):
        ''' 测试 surplus_value <= (total + cost_depreciation) '''
        self.asset.asset_done()
        self.asset.depreciation_number = 1
        self.asset.depreciation_previous = 950
        self.asset.depreciation_value = 1000
        self.wizard.create_depreciation()

    def test_create_depreciation_no_voucher_line(self):
        '''报错：本期所有固定资产都已折旧'''
        wizard = self.env['create.depreciation.wizard'].create(
            {'date': '2016-04-01'})
        with self.assertRaises(UserError):
            wizard.create_depreciation()

    def test_create_depreciation_account_diff(self):
        ''' 多个固定资产生成凭证 '''
        asset_2 = self.asset.copy()
        asset_2.asset_done()
        self.asset.asset_done()
        wizard = self.env['create.depreciation.wizard'].create({'date': '2016-05-01'})
        wizard.create_depreciation()


class TestVoucher(TransactionCase):

    def setUp(self):
        '''折旧明细准备数据'''
        super(TestVoucher, self).setUp()
        self.asset = self.env.ref('asset.asset_car')
        self.asset.is_init = True
        self.voucher = self.env.ref('finance.voucher_4')
        self.voucher.is_init = True

    def test_init_asset(self):
        '''引入固定资产'''
        with self.assertRaises(UserError):
            self.voucher.init_asset()
        self.asset.asset_done()
        self.voucher.init_asset()
        # 删除以前引入的固定资产内容，然后再引入
        self.voucher.init_asset()
